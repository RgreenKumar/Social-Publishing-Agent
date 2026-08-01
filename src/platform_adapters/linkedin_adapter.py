import os
import requests


def publish_linkedin_post(content, post_data=None, company_data=None):
    mode = os.getenv("PUBLISH_MODE", "mock").strip().lower()

    if mode != "real":
        return {
            "status": "mock",
            "platform": "linkedin",
            "message": "Mock mode: LinkedIn post not sent.",
            "payload": content,
        }

    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")

    if not access_token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN is missing")

    if not person_urn:
        raise ValueError("LINKEDIN_PERSON_URN is missing")

    text = content.get("main_post", "").strip()
    caption = content.get("caption", "").strip()
    hashtags = content.get("hashtags", "").strip()

    final_post = f"{text}\n\n{caption}\n\n{hashtags}".strip()

    url = "https://api.linkedin.com/rest/posts"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202508",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author": f"urn:li:person:{person_urn}",
        "commentary": final_post,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"LinkedIn Error {response.status_code}\n{response.text}"
        )

    return {
        "status": "posted",
        "platform": "linkedin",
        "message": "LinkedIn post published successfully.",
        "response": response.json() if response.text else {},
    }