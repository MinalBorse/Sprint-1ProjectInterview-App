"""Talks to the AI model through OpenRouter."""
# The text in triple quotes above is a "docstring": a note saying what this file is for.

# ----- Imports: bring in the tools this file needs -----
# Built into Python: turns JSON text into Python dictionaries and lists.
import json

# Built into Python: lets us read environment variables (hidden settings, like our key).
import os

# Installed with uv: load_dotenv reads the .env file.
from dotenv import load_dotenv

# Installed with uv: OpenAI is the tool that sends messages to the model.
from openai import OpenAI

# ----- Load the key -----

# Copy each line of .env (like OPENROUTER_API_KEY=...) into the environment variables.
# After this, the key is available to the program without being written in the code.
load_dotenv()


# ----- Settings -----

# Which model to use, as an OpenRouter "slug": company/model.
# In CAPITALS because it's a constant: it never changes while the app runs.
MODEL = "openai/gpt-5-mini"


# ----- Get the key, and stop early if it's missing -----

# Ask the environment for the value called OPENROUTER_API_KEY.
# If it doesn't exist, we get None (Python's word for "nothing").
api_key = os.getenv("OPENROUTER_API_KEY")

# If there's no key, stop right now with a clear message ("fail early").
# Without this, we'd still get an error later, but a confusing one.
if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to your .env file.")


# ----- Create the connection -----

# The client is the object that talks to the model. It's created once and reused.
# base_url: send requests to OpenRouter instead of OpenAI (they use the same format).
# api_key: our key, which proves we're allowed to use it.
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


# ----- The function the rest of the app will use -----


def ask_model(messages):
    """Send the conversation to the model and return its reply as text."""
    # messages is a list of dictionaries, one per message, for example:
    #   {"role": "system", "content": "You are an interviewer..."}
    #   {"role": "user", "content": "My answer is..."}

    # The actual API call: send the request to OpenRouter and wait for the answer.
    response = client.chat.completions.create(
        model=MODEL,  # which model to use
        messages=messages,  # the conversation to send
        max_tokens=2000,  # longest allowed output, including the model's hidden thinking
    )

    # The response can hold several alternative answers, called "choices".
    # We asked for one, so we take the first: [0] (Python counts from 0).
    # .message.content is the text of that answer, which we hand back.
    return response.choices[0].message.content


def ask_model_json(messages, schema):
    """Like ask_model, but asks for JSON in the shape of schema, and returns a dictionary.

    schema is a JSON schema, like REPORT_SCHEMA in prompts.py.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        # A report is longer than a single reply, and the model also thinks first,
        # so it gets more room than ask_model's 2000.
        max_tokens=4000,
        # response_format asks for JSON that matches the schema.
        response_format={"type": "json_schema", "json_schema": schema},
    )

    # The reply is JSON written as text. "or ''" turns an empty reply (None) into "".
    text = (response.choices[0].message.content or "").strip()

    # Sometimes a model wraps JSON in ```json ... ``` marks, even when asked not to.
    # Never fully trust model output: if the marks are there, remove them.
    if text.startswith("```"):
        # .split("\n", 1)[1] drops the first line (```json).
        # .rsplit("```", 1)[0] drops everything from the last ``` onwards.
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    # json.loads turns JSON text into a Python dictionary.
    return json.loads(text)


# ----- A quick test -----

# This block only runs when we start this file directly: uv run python llm.py
# When another file (like app.py) imports llm.py, this block is skipped,
# so the test isn't sent every time the app starts.
if __name__ == "__main__":
    # A test conversation: a list with one user message.
    test_messages = [
        {"role": "user", "content": "Ask me one interview question for a junior Python developer."}
    ]
    # Send it, and print the reply.
    print(ask_model(test_messages))
