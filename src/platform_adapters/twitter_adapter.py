import os
import requests


def publish_twitter_post(content, post_data=None, company_data=None):
    mode = os.getenv("PUBLISH_MODE", "mock").strip().lower()
    if mode != "real":
        return {
            "status": "mock",
            "platform": "twitter",
            "message": "Mock mode: Twitter/X post not sent.",
            "payload": content,
        }

    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

    if not bearer_token:
        raise ValueError("TWITTER_BEARER_TOKEN is missing")

    text = content.get("main_post", "").strip()
    caption = content.get("caption", "").strip()
    hashtags = content.get("hashtags", "").strip()
    tweet_text = " ".join(part for part in [text, caption, hashtags] if part).strip()
    tweet_text = tweet_text[:280]

    api_url = "https://api.twitter.com/2/tweets"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    payload = {"text": tweet_text}

    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Twitter/X post failed: {response.status_code} {response.text}")

    return {
        "status": "posted",
        "platform": "twitter",
        "message": "Twitter/X post published successfully.",
        "response": response.json() if response.text else {},
    }