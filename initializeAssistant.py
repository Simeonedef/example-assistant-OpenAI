import openai
import os
from utility import *

# This file creates a new assistant, in theory it does not need to be run as assistant is already existing.

client = set_openAIAPI()
vector_storeID = getvectorstoreID()

# Set this to true if you need to create a new vector store
CreateVectorStore = True

folder_to_upload =""

if __name__ == "__main__":
  assistant = client.beta.assistants.create(
  name="Electives assistant 4.0 mini",
  instructions="You are an academic advisor, helping students at Columbia Business School choose their electives based on their interests. Prioritize MBA classes but also offer option to explore PhD classes. You have access to a course catalog file called course_catalog.json and should always use it first to provide comprehensive answers. You should use tools to retrieve the specific course syllabus files and course page links when asked about specific courses. If no syllabus files are available do not return files that are similar, just return that no files are available. Whenever you provide course page links and syllabus links please check using tools that they are the correct links.",
  tools=[{"type": "file_search"}],
  model="gpt-4o-mini",
  )

  show_json(assistant)
  with open('newassistant.json', 'w') as f:
    json.dump(assistant.model_dump_json(), f)
  

  if CreateVectorStore:

    # Create a vector store caled "Electives information"
    vector_store_id = create_vector_store()
    
    upload_directory(folder_to_upload, vector_store_id=vector_store_id)

    # Update assistant to use new Vector store
    assistant = client.beta.assistants.update(
    assistant_id=assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )

  else:
    # Update assistant to use existing Vector store
    assistant = client.beta.assistants.update(
    assistant_id=assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_storeID]}},
    )

  