"""
This software is provided "as is," without warranty of any kind, express or implied,
including but not limited to the warranties of merchantability, fitness for a particular
purpose and noninfringement. In no event shall the authors or copyright holders be
liable for any claim, damages or other liability, whether in an action of contract,
tort or otherwise, arising from, out of or in connection with the software or the use
or other dealings in the software.

Limitation of Liability: In no event shall the authors or copyright holders be liable for any indirect, incidental, special, or consequential damages.

External Libraries: If this code relies on external libraries, please consult the disclaimers provided by those libraries.

License: MIT License.

Intended Use: This code is intended for educational purposes.
"""

import os
import requests
import json
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN")

# Check if API key is available
if not OPENAI_API_KEY:
    raise ValueError("API Key is missing. Set the OPENAI_API_KEY environment variable.")

# Initializes your app with your bot token and socket mode handler
app = App(token=SLACK_BOT_TOKEN)

# In-memory storage for user-generated content and configuration
user_content = {}
user_config = {}

# Home Tab view
def home_tab_view(client, user_id):
    blocks = [
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Configuration",
                        "emoji": True
                    },
                    "action_id": "open_configuration"
                }
            ]
        },
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

@app.action("open_configuration")
def handle_open_configuration(ack, body, client):
    ack()
    try:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "configuration_modal",
                "title": {"type": "plain_text", "text": "Configuration"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "channel_select_block",
                        "element": {
                            "type": "channels_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select a channel"
                            },
                            "action_id": "channel_select_action"
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Select channel for profile images"
                        }
                    }
                ],
                "submit": {"type": "plain_text", "text": "Save"}
            }
        )
    except Exception as e:
        logging.error(f"Error opening configuration modal: {e}")

@app.view("configuration_modal")
def handle_configuration_submission(ack, body, view):
    ack()
    user_id = body["user"]["id"]
    selected_channel = view["state"]["values"]["channel_select_block"]["channel_select_action"]["selected_channel"]
    # Store the selected channel in the in-memory storage
    user_config[user_id] = {"channel": selected_channel}
    logging.info(f"Selected channel for profile images: {selected_channel}")

@app.action("profile_picture_prompt")
def handle_some_action(ack, body, client, logger):
    ack()
    user_id = body["user"]["id"]
    
    # Clear the dictionary
    user_content.clear()
    
    # Display loading message
    blocks = home_tab_view(client, user_id)["blocks"]

    # Clear existing preview blocks and loading message
    blocks = [block for block in blocks if block.get("type") not in ["image", "header", "context", "section"] or block.get("text", {}).get("text") != ":hourglass: Generating your profile picture, please wait..."]
    
    # Add loading message
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ":hourglass: Generating your profile picture, please wait..."
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
    
    # System prompt to be prefixed to the user's prompt
    system_prompt = "You are generating a Slack profile. Strictly ensure images should be well framed and the person should be looking straight on. DO NOT include other people in the image, it should be of an individual only. DO NOT include text. Image should be realistic not cartoon. Generate a slack profile with the following description:"
    
    # Request data - customize as needed
    user_prompt = body["actions"][0]["value"]
    full_prompt = system_prompt + user_prompt
    payload = {
        "model": "dall-e-3",  # Change to "dall-e-2" if you want to use DALL·E 2
        "prompt": full_prompt,  # Use the full prompt with the system prompt prefixed
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
            new_blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":x: Delete"
                        },
                        "action_id": "delete_image"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":slack: Update user profile"
                        },
                        "action_id": "update_user_profile"
                    }
                ]
            })
        
        # Store the new blocks in the in-memory storage
        user_content[user_id] = new_blocks
        
        # Update the view with the new blocks
        blocks = [block for block in blocks if block.get("type") != "section" or block.get("text", {}).get("text") != ":hourglass: Generating your profile picture, please wait..."]
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

@app.action("delete_image")
def handle_delete_image(ack, body, client, logger):
    ack()
    user_id = body["user"]["id"]
    
    # Clear the user content for the specific user
    if user_id in user_content:
        del user_content[user_id]
    
    # Update the home tab view
    view = home_tab_view(client, user_id)
    try:
        response = client.views_publish(user_id=user_id, view=view)
        logging.debug(f"View updated successfully after deleting image: {response}")
    except Exception as e:
        logging.error(f"Error updating view after deleting image: {e}")

@app.action("update_user_profile")
def handle_update_user_profile(ack, body, client, logger):
    ack()
    user_id = body["user"]["id"]
    
    # Open a dialog for updating the user profile
    try:
        response = client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "update_profile_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Update User Profile"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "user_select_block",
                        "element": {
                            "type": "users_select",
                            "action_id": "user_select_action",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select a user"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "User"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "first_name_block",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "first_name_action"
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "First Name"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "last_name_block",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "last_name_action"
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Last Name"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "job_title_block",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "job_title_action"
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Job Title"
                        }
                    }
                ],
                "submit": {
                    "type": "plain_text",
                    "text": "Confirm"
                }
            }
        )
        logging.debug(f"Dialog opened successfully: {response}")
    except Exception as e:
        logging.error(f"Error opening dialog: {e}")

# Start your app
if __name__ == "__main__":
    logging.info("Starting the Slack app...")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
