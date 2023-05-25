import os
import modal
from typing import Dict

# Constants
STUB = modal.Stub("smol-debugger-v1")
GENERATED_DIR = "generated"
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico', '.tif', '.tiff']
OPENAI_IMAGE = modal.Image.debian_slim().pip_install("openai")

def read_file(filename: str) -> str:
    """
    Reads a file and returns its content.
    """
    with open(filename, 'r') as file:
        return file.read()

def is_image(file: str) -> bool:
    """
    Checks if a file is an image by its extension.
    """
    return any(file.endswith(ext) for ext in IMAGE_EXTENSIONS)

def walk_directory(directory: str) -> Dict[str, str]:
    """
    Walks through a directory and returns a dictionary with the relative file path
    and its content. Only non-image files are included.
    """
    code_contents = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not is_image(file):
                relative_filepath = os.path.relpath(os.path.join(root, file), directory)
                try:
                    code_contents[relative_filepath] = read_file(os.path.join(root, file))
                except Exception as e:
                    code_contents[relative_filepath] = f"Error reading file {file}: {e}"
    return code_contents

@STUB.local_entrypoint()
def main(prompt: str, directory=GENERATED_DIR, model="gpt-3.5-turbo"):
    """
    Main function to debug a program for a user based on their file system.
    """
    code_contents = walk_directory(directory)

    context = "\n".join(f"{path}:\n{contents}" for path, contents in code_contents.items())
    system_prompt = "You are an AI debugger who is trying to debug a program for a user based on their file system. The user has provided you with the following files and their contents, finally followed by the error message or issue they are facing."
    user_prompt = f"My files are as follows: {context}\n\nMy issue is as follows: {prompt}\n\nGive me ideas for what could be wrong and what fixes to do in which files."

    res = generate_response.call(system_prompt, user_prompt, model)

    # Print response in teal
    print(f"\033[96m{res}\033[0m")

@STUB.function(
    image=OPENAI_IMAGE,
    secret=modal.Secret.from_dotenv(),
    retries=modal.Retries(
        max_retries=3,
        backoff_coefficient=2.0,
        initial_delay=1.0,
    ),
    concurrency_limit=5,
    timeout=120,
)
def generate_response(system_prompt: str, user_prompt: str, model="gpt-3.5-turbo", *args) -> str:
    """
    Generates a response from OpenAI's API based on the system and user prompts.
    """
    import openai

    # Set up your OpenAI API credentials
    openai.api_key = os.getenv("OPENAI_API_KEY")

    messages = [{"# Continue from previous message
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    role = "assistant"
    for value in args:
        messages.append({"role": role, "content": value})
        role = "user" if role == "assistant" else "assistant"

    params = {
        'model': model,
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0,
    }

    # Send the API request
    response = openai.ChatCompletion.create(**params)

    # Get the reply from the API response
    reply = response.choices[0]["message"]["content"]
    return reply
