import os
import requests


def publish_facebook_post(content, post_data=None, company_data=None):
    mode = os.getenv("PUBLISH_MODE", "mock").strip().lower()
    if mode != "real":
        return {
            "status": "mock",
            "platform": "facebook",
            "message": "Mock mode: Facebook post not sent.",
            "payload": content,
        }

    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")

    if not access_token:
        raise ValueError("FACEBOOK_ACCESS_TOKEN is missing")
    if not page_id:
        raise ValueError("FACEBOOK_PAGE_ID is missing")

    message = content.get("main_post", "").strip()
    caption = content.get("caption", "").strip()
    hashtags = content.get("hashtags", "").strip()
    full_message = f"{message}\n\n{caption}\n\n{hashtags}".strip()

    api_url = f"https://graph.facebook.com/v20.0/{page_id}/feed"
    payload = {
        "message": full_message,
        "access_token": access_token,
    }

    response = requests.post(api_url, data=payload, timeout=30)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Facebook post failed: {response.status_code} {response.text}")

    return {
        "status": "posted",
        "platform": "facebook",
        "message": "Facebook post published successfully.",
        "response": response.json() if response.text else {},
    }