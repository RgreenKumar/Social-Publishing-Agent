import os
import requests


def publish_instagram_post(content, post_data=None, company_data=None):
    mode = os.getenv("PUBLISH_MODE", "mock").strip().lower()
    if mode != "real":
        return {
            "status": "mock",
            "platform": "instagram",
            "message": "Mock mode: Instagram post not sent.",
            "payload": content,
        }

    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    ig_user_id = os.getenv("INSTAGRAM_USER_ID")

    if not access_token:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN is missing")
    if not ig_user_id:
        raise ValueError("INSTAGRAM_USER_ID is missing")

    caption = content.get("main_post", "").strip()
    post_caption = content.get("caption", "").strip()
    hashtags = content.get("hashtags", "").strip()
    full_caption = f"{caption}\n\n{post_caption}\n\n{hashtags}".strip()

    create_media_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media"
    publish_media_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish"

    media_payload = {
        "caption": full_caption,
        "access_token": access_token,
    }

    media_response = requests.post(create_media_url, data=media_payload, timeout=30)
    if media_response.status_code not in (200, 201):
        raise RuntimeError(f"Instagram media creation failed: {media_response.status_code} {media_response.text}")

    creation_id = media_response.json().get("id")
    if not creation_id:
        raise RuntimeError("Instagram media creation did not return an id")

    publish_payload = {
        "creation_id": creation_id,
        "access_token": access_token,
    }

    publish_response = requests.post(publish_media_url, data=publish_payload, timeout=30)
    if publish_response.status_code not in (200, 201):
        raise RuntimeError(f"Instagram publish failed: {publish_response.status_code} {publish_response.text}")

    return {
        "status": "posted",
        "platform": "instagram",
        "message": "Instagram post published successfully.",
        "response": publish_response.json() if publish_response.text else {},
    }