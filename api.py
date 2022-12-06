import logging
import json

from flask import Flask, request, abort
from Classes import auth, chat

logger = logging.getLogger(__name__)
app = Flask(__name__)




def get_credentials():
    with open("config.json", "r") as f:
        config = json.load(f)
    # Check if email & password are in config.json
    if "email" not in config or "password" not in config:
        raise LookupError("config.json is missing email or password. Please add them.")

    # Get email & password
    return config["email"], config["password"]

def get_state():
    try:
        with open("state.json", "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}
    return state

def set_state(state):
    with open("state.json", "w") as f:
        json.dump(state, f)

@app.route("/", methods=["POST"])
def query():
    data = request.json
    print(data)

    query = data.get("query")
    logging.info(f"Received query: {query}")

    if not query:
        abort(400, description="No query provided.")

    expired_creds = auth.expired_creds()
    if expired_creds:
        try:
            email, password = get_credentials()
        except LookupError as e:
            logging.error(e)
            abort(500, description=str(e))
        
        open_ai_auth = auth.OpenAIAuth(email_address=email, password=password)
        open_ai_auth.begin()

        if auth.expired_creds():
            abort(500, description="Failed to refresh credentials. Please try again.")

    access_token = auth.get_access_token()

    state = get_state()
    answer, previous_convo, convo_id = chat.ask(auth_token=access_token,
                                            prompt=query,
                                            conversation_id=state.get("conversation_id"),
                                            previous_convo_id=state.get("previous_convo_id"))

    if answer == "400" or answer == "401":
        auth.delete_token()
        abort(500, description="Your token is invalid. Please try again.")
        
    state["conversation_id"] = convo_id
    state["previous_convo_id"] = previous_convo
    set_state(state)

    return answer

@app.route("/reset", methods=["POST"])
def reset():
    state = get_state()
    state["conversation_id"] = None
    state["previous_convo_id"] = None
    set_state(state)
    auth.delete_token()
    return "OK"



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)
