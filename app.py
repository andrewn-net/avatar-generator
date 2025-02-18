import os
import requests
import json
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

# Check if API key is available
if not OPENAI_API_KEY:
    raise ValueError("API Key is missing. Set the OPENAI_API_KEY environment variable.")

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# In-memory storage for user-generated content
user_content = {}

# Home Tab view
def home_tab_view(client, user_id):
    blocks = [
        {
            "dispatch_action": True,
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "profile_picture_prompt"
            },
            "label": {
                "type": "plain_text",
                "text": "Describe your desired profile picture",
                "emoji": True
            }
        }
    ]
    
    # Retrieve user-generated content if available
    if user_id in user_content:
        blocks.extend(user_content[user_id])
    
    view = {
        "type": "home",
        "blocks": blocks
    }
    logging.debug(f"Home tab view: {view}")
    return view

# App Home Opened Event
@app.event("app_home_opened")
def update_home_tab(client, event):
    user_id = event["user"]
    logging.debug(f"App home opened for user: {user_id}")
    view = home_tab_view(client, user_id)
    try:
        response = client.views_publish(user_id=user_id, view=view)
        logging.debug(f"View published successfully: {response}")
    except Exception as e:
        logging.error(f"Error publishing view: {e}")

@app.action("profile_picture_prompt")
def handle_some_action(ack, body, client, logger):
    ack()
    user_id = body["user"]["id"]
    
    # Clear the dictionary
    user_content.clear()
    
    # Display loading message
    blocks = home_tab_view(client, user_id)["blocks"]

    # Add loading message
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Generating your profile picture, please wait..."
        }
    })
    
    view = {
        "type": "home",
        "blocks": blocks
    }
    try:
        response = client.views_publish(user_id=user_id, view=view)
        logging.debug(f"View updated with loading message: {response}")
    except Exception as e:
        logging.error(f"Error updating view with loading message: {e}")

    # API endpoint for image generation
    url = "https://api.openai.com/v1/images/generations"
    
    # Request data - customize as needed
    payload = {
        "model": "dall-e-3",  # Change to "dall-e-2" if you want to use DALL·E 2
        "prompt": body["actions"][0]["value"],  # Use the prompt from the input
        "n": 1,  # Number of images to generate (between 1 and 10)
        "size": "1024x1024",  # Set to "256x256", "512x512", or "1024x1024" for DALL·E 2, or for DALL·E 3
    }

    # Headers for the request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    # Send the request to OpenAI API
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response
        data = response.json()
        image_urls = [image["url"] for image in data["data"]]

        # Update the home tab with the generated image URL
        new_blocks = []
        for url in image_urls:
            new_blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "AI Generated Profile Picture",
                    "emoji": True
                }
            })
            new_blocks.append({
                "type": "image",
                "image_url": url,
                "alt_text": "Generated Image"
            })
            new_blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Note: This image will expire in 60 minutes. Please update your profile before then."
                    }
                ]
            })
        
        # Store the new blocks in the in-memory storage
        user_content[user_id] = new_blocks
        
        # Update the view with the new blocks
        blocks = [block for block in blocks if block.get("type") != "section" or block.get("text", {}).get("text") != "Generating your profile picture, please wait..."]
        blocks.extend(new_blocks)
        view = {
            "type": "home",
            "blocks": blocks
        }
        try:
            response = client.views_publish(user_id=user_id, view=view)
            logging.debug(f"View updated successfully with image URL: {response}")
        except Exception as e:
            logging.error(f"Error updating view with image URL: {e}")
    else:
        # Handle errors
        logging.error(f"Error: {response.status_code} - {response.text}")
    logger.info(body)

# Start your app
if __name__ == "__main__":
    logging.info("Starting the Slack app...")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
