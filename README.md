# example-assistant-OpenAI

Example assistant with boiler plate python code that implements vector storage DB and one example tool call function available to the assistant.


## Initialization & running
Please set the following parameters in utility.py
```
# Set parameters
vectorStoreID=""
assistant_ID = ""
api_key=''
```

If this is your first time running and do not have a vector storage or assistant yet then you will need to initialize a new assistant and vector storage using initializeAssistant.py

### Creating a new assistant and vector storage
```
python initializeAssistant.py
```

Running this file will create an assistant with the specified prompt. The assistant's information will be saved to a json file and you can retrieve the assistant id to set it in utility.py
If the flag on line 11 is set to true, (by default True) then a vector storage will also be created and attached to the assistant.

Files in the specified data folder will be uploaded to the vector storage.

### Running
To initiate hooking into the assistant and talking to it, run 
```
python streamMessage.py
```

## Utility functions
For easy updating of the vector storage on OpenAI, the utility.py file groups some useful functions. Feel free to run it and visit functions.