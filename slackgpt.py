# -----------------------------------------------------------------------------
# Directed by Aaron Ng (@localghost)
# Co-authored by ChatGPT powered by GPT-4
# -----------------------------------------------------------------------------

import openai
import os
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

# Local dev only.
# from dotenv import load_dotenv
# load_dotenv()

# Configuration
DEFAULT_PROMPT = (
    "You are a friendly assistant for a company that can answer general questions "
    "about business, marketing, and programming. Your goal is to help the people in "
    "the company with any questions they might have. If you aren't sure about "
    "something or something seems inappropriate, you should say that you don't know."
)
# The OpenAI model to use. Can be gpt-3.5-turbo or gpt-4.
MODEL = os.environ.get("MODEL", "gpt-3.5-turbo")
# The max length of a message to OpenAI.
MAX_TOKENS = 8000 if MODEL == "gpt-4" else 4096
# The max length of a response from OpenAI.
MAX_RESPONSE_TOKENS = 1000
# Starts with "sk-", used for connecting to OpenAI.
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# Starts with "xapp-", used for connecting to Slack.
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
# Starts with "xoxb-", used for connecting to Slack.
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
# Tokens are ~4 characters but this script doens't account for that yet.
TOKEN_MULTIPLIER = 4  

# Initialize the Slack Bolt App and Slack Web Client
app = App()
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# Set up the default prompt and OpenAI API
prompt = os.environ.get("PROMPT", DEFAULT_PROMPT)
openai.api_key = OPENAI_API_KEY


def generate_completion(prompt, messages):
    """Generate a completion using OpenAI API."""
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "system", "content": prompt}] + messages,
        max_tokens=MAX_RESPONSE_TOKENS,
        n=1,
        stop=None,
        temperature=0.7,
    )

    completion = response.choices[0].message["content"].strip()
    return completion


def get_message_history(channel_id, user_id, event_ts, limit, thread=False):
    """Fetch conversation or thread history and build a list of messages."""
    history = []

    # Fetch the message history
    if thread:
        result = slack_client.conversations_replies(
            channel=channel_id, ts=event_ts, limit=limit, latest=int(time.time())
        )
    else:
        result = slack_client.conversations_history(
            channel=channel_id, limit=limit
        )

    token_count = 0
    for message in result["messages"]:
        if message.get("user") == user_id:
            role = "user"
        elif message.get("subtype") == "bot_message" or message.get("bot_id"):
            role = "assistant"
        else:
            continue

        token_count += len(message["text"])
        if token_count > (MAX_TOKENS - MAX_RESPONSE_TOKENS):
            break
        else:
            history.append({"role": role, "content": message["text"]})

    # DMs are in reverse order while threads are not.
    if not thread:
        history.reverse()

    return history


def handle_message(event, thread=False):
    """Handle a direct message or mention."""
    channel_id = event["channel"]
    user_id = event["user"]
    event_ts = event["ts"]

    # Set up the payload for the "Typing a response..." message
    payload = {"channel":channel_id, "text": "Typing a response..."}

    if thread:
        # Use the thread_ts as the event_ts when in a thread
        event_ts = event.get("thread_ts", event["ts"])
        payload["thread_ts"] = event_ts

    # Get message history
    history = get_message_history(
        channel_id, user_id, event_ts, limit=25, thread=thread
    )
        
    # Send "Typing a response..." message
    typing_message = slack_client.chat_postMessage(
        **payload
    )

    # Generate the completion
    try:
        completion_message = generate_completion(prompt, history)
    except Exception as e:
        completion_message = (
            "The call to OpenAI or another external service failed. Please try again later."
        )

    # Replace "Typing a response..." with the actual response
    slack_client.chat_update(
        channel=channel_id, ts=typing_message["ts"], text=completion_message
   
    )

@app.event("app_mention")
def mention_handler(body, say):
    """Handle app mention events."""
    event = body["event"]
    handle_message(event, thread=True)

@app.event("message")
def direct_message_handler(body, say):
    """Handle direct message events."""
    event = body["event"]
    if event.get("subtype") == "bot_message" or event.get("bot_id"):
        return
    handle_message(event)

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
