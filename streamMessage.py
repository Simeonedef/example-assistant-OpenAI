from typing_extensions import override
from openai import AssistantEventHandler
from openai import OpenAI
from utility import *
from colorama import Fore, Style
import time
from datetime import datetime

def parse_time(time_str):
    """Helper function to convert time strings like '10:50 AM' or '14:20' to datetime.time objects."""
    try:
        # Try parsing 12-hour format with AM/PM (e.g., '10:50 AM')
        return datetime.strptime(time_str, '%I:%M %p').time()
    except ValueError:
        # If it fails, try parsing 24-hour format (e.g., '14:20')
        return datetime.strptime(time_str, '%H:%M').time()

def check_date_overlap(start1, end1, start2, end2):
    """Check if two date ranges overlap."""
    return max(start1, start2) <= min(end1, end2)

def check_schedule_conflict(courses: list) -> str:
    """
    Check if any courses have conflicting schedules.

    Args:
        courses (list): List of dictionaries, each containing class details:
            - class_name
            - start_date
            - end_date
            - days_of_week
            - start_time
            - end_time

    Returns:
        str: Message indicating if conflicts were found or not.
    """
    for i, course1 in enumerate(courses):
        start_date1 = datetime.strptime(course1['start_date'], '%Y-%m-%d').date()
        end_date1 = datetime.strptime(course1['end_date'], '%Y-%m-%d').date()
        start_time1 = parse_time(course1['start_time'])
        end_time1 = parse_time(course1['end_time'])

        for j, course2 in enumerate(courses):
            if i != j:
                start_date2 = datetime.strptime(course2['start_date'], '%Y-%m-%d').date()
                end_date2 = datetime.strptime(course2['end_date'], '%Y-%m-%d').date()
                start_time2 = parse_time(course2['start_time'])
                end_time2 = parse_time(course2['end_time'])

                # Check if the courses overlap in dates
                if check_date_overlap(start_date1, end_date1, start_date2, end_date2):
                    # Check if they share any days of the week
                    if set(course1['days_of_week']).intersection(set(course2['days_of_week'])):
                        # Check if their times overlap
                        if (start_time1 < end_time2) and (end_time1 > start_time2):
                            return f"Conflict found between {course1['class_name']} and {course2['class_name']}."
    
    return "No conflicts detected."

# Define the tool schema (function definition)
tools = [{"type": "file_search"},
      {
        "type": "function",
        "function": {
            "name": "check_schedule_conflict",
            "description": "Check if any courses have conflicting schedules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "courses": {
                        "type": "array",
                        "description": "List of courses with their schedules to check for conflicts.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "class_name": { "type": "string" },
                                "start_date": { "type": "string" },
                                "end_date": { "type": "string" },
                                "days_of_week": { "type": "array", "items": { "type": "string" } },
                                "start_time": { "type": "string" },
                                "end_time": { "type": "string" }
                            },
                            "required": ["class_name", "start_date", "end_date", "days_of_week", "start_time", "end_time"]
                        }
                    }
                },
                "required": ["courses"]
            }
        }
      },
]

def callTools(tool_calls):
    tool_outputs = []
    for t in tool_calls:
        function_name = t.function.name
        attributes = json.loads(t.function.arguments)
        print(function_name)

        try:
            if function_name == "check_schedule_conflict":
                # Call the custom function
                # print(attributes)
                courses = attributes.get("courses", [])
                # print(courses)
                function_response = globals()[function_name](courses)
                # print(function_response)
            else:
                function_response = {"status": f"Unknown function '{function_name}' called."}
        except Exception as e:
            # We just tell OpenAI there was an error
            function_response = {"status": f"Error in function call {function_name}({t.function.arguments}): {str(e)}"}
        
        tool_outputs.append({
            "tool_call_id": t.id,
            "output": json.dumps(function_response)
        })

    return tool_outputs

client = set_openAIAPI()

# This is the GPT 3.5 assistant
# assistantID = "asst_usw3ah4l7Uk3ybzsWTuznsVW"

# This is the GPT 4.0 mini assistant
assistantID = getassistantID()


thread = client.beta.threads.create()
# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.
 
class EventHandler(AssistantEventHandler):    
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
      
    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
      
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)
  
    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)


    @override
    def on_message_done(self, message) -> None:
        # print a citation to the file searched
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        print("\n".join(citations))
 
# Then, we use the `stream` SDK helper 
# with the `EventHandler` class to create the Run 
# and stream the response.

tool_outputs = []
 
with client.beta.threads.runs.stream(
  thread_id=thread.id,
  assistant_id=assistantID,
  event_handler=EventHandler(),
  max_prompt_tokens=5000
) as stream:
  stream.until_done()


def check_run(client, thread_id, run_id):
    while True:
        # Refresh the run object to get the latest status
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )

        if run.status == "completed":
            print(f"{Fore.GREEN} Run is completed.{Style.RESET_ALL}")
            break
        elif run.status == "expired":
            print(f"{Fore.RED}Run is expired.{Style.RESET_ALL}")
            break
        elif run.status =="requires_action":
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = callTools(tool_calls)
            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        else:
            print(f"{Fore.YELLOW} OpenAI: Run is not yet completed. Waiting...{run.status} {Style.RESET_ALL}")
            time.sleep(3)  # Wait for 1 second before checking again

def chat_loop(client, assistant, thread):
    while True:
        # Input from user

        user_input = input(f"{Fore.CYAN} User: ")
        print(Style.RESET_ALL)
        if user_input == "quit":
            break

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistantID,
            tools=tools
        )

        check_run(client, thread.id, run.id)

        # Get the latest messages from the thread
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )

        # Get the latest message from the user
        user_message = messages.data[1].content[0].text.value

        # Get the latest message from the assistant
        assistant_message = messages.data[0].content[0].text

        # Print the latest message from the user
        # print(f"{Fore.CYAN} User: {user_message} {Style.RESET_ALL}")

        message_content = assistant_message

        # Need to fix Citations, so code is commented out for the moment
        # annotations = message_content.annotations
        # citations = []
        # # Iterate over the annotations and add footnotes
        # for index, annotation in enumerate(annotations):
        #     # Replace the text with a footnote
        #     message_content.value = message_content.value.replace(annotation.text, f' [{index}]')
        
        #     # Gather citations based on annotation attributes
        #     if (file_citation := getattr(annotation, 'file_citation', None)):
        #         cited_file = client.files.retrieve(file_citation.file_id)
        #         citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
        #     elif (file_path := getattr(annotation, 'file_path', None)):
        #         cited_file = client.files.retrieve(file_path.file_id)
        #         citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
        #         # Note: File download functionality not implemented above for brevity
        
        # # Add footnotes to the end of the message before displaying to user
        # message_content.value += '\n' + '\n'.join(citations)

        # Print the latest message from the assistant
        print(f"{Fore.BLUE} Assistant: {message_content.value} {Style.RESET_ALL}")




def main():
    chat_loop(client, assistantID, thread)

if __name__ == "__main__":
    main()
