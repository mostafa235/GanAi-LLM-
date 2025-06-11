import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get("https://huggingface.co/api/models/gpt2", headers=headers)

print("Status code:", response.status_code)
print("Response:", response.json())
import os
load_dotenv()
print("Token loaded:", os.getenv("HUGGINGFACEHUB_API_TOKEN") is not None)
