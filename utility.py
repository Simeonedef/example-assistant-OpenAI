import openai
import os
import json
import datetime
import requests

# Set parameters
vectorStoreID=""
assistant_ID = ""
api_key=''

# read prompt from file
with open('prompt.txt', 'r') as f:
    prompt_input = f.read()

def show_json(obj):
    print(json.loads(obj.model_dump_json()))

def set_openAIAPI():
    # Set up OpenAI API key
    client = openai.OpenAI(api_key=api_key)
    return client

def getassistantID_fromOpenAI():
    client = set_openAIAPI()
    response = client.beta.assistants.list()
    assistant_ID = response.data[0].id
    print(response.data[0])
    return assistant_ID

def getvectorstoreID():
    return vectorStoreID

def getassistantID():
    return assistant_ID

def create_vector_store():
    client = set_openAIAPI()
    vector_store = client.beta.vector_stores.create(name="Electives information")
    print("Created vector store with id: " + vector_store.id)
    return vector_store.id

def list_files():
    client = set_openAIAPI()
    response = client.files.list(purpose="assistants")
    file_ids = []
    if len(response.data) == 0:
        print("No files found.")
        return
    print(f"Found {len(response.data)} files.")
    for file in response.data:
        created_date = datetime.datetime.utcfromtimestamp(file.created_at).strftime('%Y-%m-%d')
        print(f"{file.filename} [{file.id}], Created: {created_date}")
        file_ids.append(file.id)
    return file_ids

def list_files_store():
    client = set_openAIAPI()
    vector_store = client.beta.vector_stores.retrieve(vectorStoreID)
    print("Vector store object: ", vector_store)

    vector_store_files = client.beta.vector_stores.files.list(
        vector_store_id=vectorStoreID, limit=100
    )
    return(vector_store_files)

def retrieve_file(file_id):
    client = set_openAIAPI()
    return(client.files.retrieve(file_id))

def delete_file_from_vector(file_id):
    client = set_openAIAPI()
    deleted_vector_store_file = client.beta.vector_stores.files.delete(
    vector_store_id=vectorStoreID,
    file_id=file_id
    )
    print(deleted_vector_store_file)

def delete_file(file_id):
    client = set_openAIAPI()
    print(client.files.delete(file_id))

#return file id for given filename inside of vector store
def look_for_file_in_vector(filename):
    vector_store_list=list_files_store()
    vector_store_json = json.loads(vector_store_list.model_dump_json())

    file_to_search=filename
    file_ids = []

    for file in vector_store_json["data"]:
        
        file_info = retrieve_file(file["id"])
        file_info_json = json.loads(file_info.model_dump_json())
        if file_info_json["filename"] == file_to_search:
            file_ids.append(file["id"])

        print("found %d files \n", len(file_ids))    
        return(file_ids)

# return file id for given filename        
def look_for_file(filename):
    client = set_openAIAPI()
    file_list=client.files.list()
    file_list_json = json.loads(file_list.model_dump_json())

    file_to_search=filename

    file_ids = []

    for file in file_list_json["data"]:
        if file["filename"] == file_to_search:
            file_ids.append(file["id"])
    
    print("found %d files \n", len(file_ids))          
    return(file_ids)


# upload file and add to vector storage
def upload_file(filename, vector_store_ID=vectorStoreID):
    client = set_openAIAPI()
    try:
        with open(filename, "rb") as file:
            response = client.files.create(file=file, purpose="assistants")
            print(response)
            filename = retrieve_file(response.id).filename
            print(f"File uploaded successfully: {filename} [{response.id}]")
            add_file(response.id, vector_store_ID)
    except FileNotFoundError:
        print("File not found. Please make sure the filename and path are correct.")
    
# Adds file to vector storage
def add_file(file_id, vector_store_ID=vectorStoreID):
    client = set_openAIAPI()
    vector_store_file = client.beta.vector_stores.files.create_and_poll(
    vector_store_id=vector_store_ID,
    file_id=file_id
    )
    print(vector_store_file)

# remove current file and reupload new file - has to be the same name for file
def update_file():
    filename = input("Enter the filename, or type 'exit' to cancel: ")
    if filename == 'exit':
        print("Operation cancelled")
        return
    else:
        # remove file
        files_to_remove = look_for_file(filename)
        for file in files_to_remove:
            delete_file(file)

        # reupload file
        upload_file(filename)
        look_for_file_in_vector(filename)

def list_and_delete_file():
    client = set_openAIAPI()
    while True:
        response = list_files_store()
        files = list(response.data)
        if len(files) == 0:
            print("No files found.")
            return
        for i, file in enumerate(files, start=1):
            created_date = datetime.datetime.utcfromtimestamp(file.created_at).strftime('%Y-%m-%d')
            filename = retrieve_file(file.id).filename
            print(f"[{i}] {filename} [{file.id}], Created: {created_date}")
        choice = input("Enter a file number to delete, or any other input to return to menu: ")
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(files):
            return
        selected_file = files[int(choice) - 1]
        client.files.delete(selected_file.id)
        filename = retrieve_file(selected_file.id).filename
        print(f"File deleted: {filename}")

def delete_all_files():
    choice = input("Type 1 to delete all files from vector storage, type 2 for all files on OpenAI:")
    if choice == '1':
        confirmation = input("This will delete all OpenAI files from specified vector storage.\n Type 'YES' to confirm: ")
        if confirmation == "YES":
            response = list_files_store()
            for file in response.data:
                print(f"Deleting {retrieve_file(file.id).filename} [{file.id}]")
                delete_file_from_vector(file.id)
            print("All files from vector store have been deleted.")
        else:
            print("Operation cancelled.")
    elif choice=='2':
        client = set_openAIAPI()
        confirmation = input("This will delete all OpenAI files.\n Type 'YES' to confirm: ")
        if confirmation == "YES":
            response = client.files.list(purpose="assistants")
            for file in response.data:
                print(f"Deleting {retrieve_file(file.id).filename} [{file.id}]")
                delete_file(file.id)
            print("All files from OpenAI have been deleted.")
        else:
            print("Operation cancelled.")

def upload_directory(directory, vector_store_ID=vectorStoreID):
    for root, dirs, files in os.walk(directory):
        file_ids =[]
        for file in files:
            file_path = os.path.join(root, file)
            # print(file_path)
            upload_file(file_path, vector_store_ID)

def add_all_files_to_storage():
    file_ids = list_files()
    client = set_openAIAPI()
    vector_store_file_batch = client.beta.vector_stores.file_batches.create_and_poll(
    vector_store_id=vectorStoreID,
    file_ids=file_ids
    )
    print(vector_store_file_batch)
    with open("batch_info.txt", "w") as f:
        f.write(vector_store_file_batch)

def change_prompt(prompt):
    client = set_openAIAPI()

    updated_assistant = client.beta.assistants.update(
    assistant_ID,
    instructions=prompt,
    )

    print(updated_assistant)
    with open('assistant_latest.json', 'w') as f:
        json.dump(updated_assistant.model_dump_json(), f)


def main():
    while True:
        print("\n== Assistants file utility ==")
        print("[1] Upload file and add to vector storage")
        print("[2] List all files on OpenAI / vector store")
        print("[3] List all and delete one of your choice")
        print("[4] Delete all files from OpenAI / vector store (confirmation required)")
        print("[5] Update file")
        print("[6] Upload entire directory")
        print("[7] Add all files on OpenAI to vector store")
        print("[8] Change the assistant's prompt")
        print("[9] Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            filename = input("Enter the filename to upload: ")
            upload_file(filename)
        elif choice == "2":
            choice = input("Type 1 to list all files from vector storage, type 2 for all files on OpenAI:")
            if choice == '1':
                response=list_files_store()
                print(f"Found {len(response.data)} files.")
                if len(response.data) == 0:
                    print("No files found.")
                    return
                for file in response.data:
                    fileinfo = retrieve_file(file.id)
                    filename = fileinfo.filename
                    fileid = file.id
                    created_date = datetime.datetime.utcfromtimestamp(file.created_at).strftime('%Y-%m-%d')
                    print(f"{filename} [{fileid}], Created: {created_date}")
            elif choice == '2':
                list_files()
            else:
                print("Wrong input, returning to menu")
        elif choice == "3":
            list_and_delete_file()
        elif choice == "4":
            delete_all_files()
        elif choice =='5':
            update_file()
        elif choice =='6':
            directory = input("Input directory name or type 'exit' to return: ")
            if directory == 'exit':
                break
            else:
                upload_directory(directory)
        elif choice =='7':
            add_all_files_to_storage()
        elif choice =="8":
            print("Changing prompt to:")
            prompt = prompt_input
            print(prompt)
            change_prompt(prompt)
        elif choice == "9":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()





