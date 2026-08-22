import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("LINKEDIN_ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {token}",
    "X-Restli-Protocol-Version": "2.0.0"
}

url = "https://api.linkedin.com/v2/me"
response = requests.get(url, headers=headers)

print("Status:", response.status_code)
print(response.text)