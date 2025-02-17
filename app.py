import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from the environment variable
API_KEY = os.getenv("OPENAI_API_KEY")  # Set this in your .env or environment variables

# Check if API key is available
if not API_KEY:
    raise ValueError("API Key is missing. Set the OPENAI_API_KEY environment variable.")

# API endpoint for image generation
url = "https://api.openai.com/v1/images/generations"

# Request data - customize as needed
payload = {
    "model": "dall-e-3",  # Change to "dall-e-2" if you want to use DALL·E 2
    "prompt": "A cute baby sea otter",  # Change this prompt to your own description
    "n": 1,  # Number of images to generate (between 1 and 10)
    "size": "1024x1024",  # Set to "256x256", "512x512", or "1024x1024" for DALL·E 2, or for DALL·E 3
}

# Headers for the request
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

# Send the request to OpenAI API
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Check if the request was successful
if response.status_code == 200:
    # Parse the response
    data = response.json()
    image_urls = [image["url"] for image in data["data"]]

    # Print or return the image URLs
    print("Generated Image(s):")
    for url in image_urls:
        print(url)
else:
    # Handle errors
    print(f"Error: {response.status_code} - {response.text}")
