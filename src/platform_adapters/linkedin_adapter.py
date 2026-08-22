import os
import requests


from dotenv import load_dotenv
load_dotenv()


LINKEDIN_API_VERSION = os.getenv("LINKEDIN_API_VERSION", "202608")


def publish_linkedin_post(content, post_data=None, company_data=None):
    mode = os.getenv("PUBLISH_MODE", "mock").strip().lower()


    # ---------------- MOCK MODE ----------------
    if mode != "real":
        return {
            "status": "mock",
            "platform": "linkedin",
            "message": "Mock mode: LinkedIn post not sent.",
            "payload": content,
        }


    # ---------------- ENV ----------------
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")


    if not access_token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN is missing")


    if not person_urn:
        raise ValueError("LINKEDIN_PERSON_URN is missing")


    # ---------------- CONTENT ----------------
    if isinstance(content, dict):
        final_post = "\n\n".join(
            str(part).strip()
            for part in [
                content.get("main_post"),
                content.get("caption"),
                content.get("hashtags"),
            ]
            if part
        )
    else:
        final_post = str(content).strip()


    image_urn = None


    if isinstance(post_data, dict):
        image_bytes = post_data.get("image_bytes")
        image_filename = post_data.get("image_filename", "image.jpg")
    else:
        image_bytes = None
        image_filename = "image.jpg"


    if image_bytes:
        # STEP 1: Initialize image upload
        init_url = "https://api.linkedin.com/rest/images?action=initializeUpload"


        init_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }


        owner_urn = person_urn if str(person_urn).startswith("urn:li:person:") else f"urn:li:person:{person_urn}"


        init_body = {
            "initializeUploadRequest": {
                "owner": owner_urn
            }
        }


        init_response = requests.post(
            init_url,
            headers=init_headers,
            json=init_body,
            timeout=30,
        )


        if init_response.status_code not in (200, 201):
            raise RuntimeError(
                f"LinkedIn image init error {init_response.status_code}\n{init_response.text}"
            )


        init_data = init_response.json()
        upload_url = init_data["value"]["uploadUrl"]
        image_urn = init_data["value"]["image"]


        # STEP 2: Upload binary image to the signed upload URL
        upload_headers = {
            "Content-Type": "application/octet-stream",
        }


        upload_response = requests.put(
            upload_url,
            headers=upload_headers,
            data=image_bytes,
            timeout=30,
        )


        if upload_response.status_code not in (200, 201, 202):
            raise RuntimeError(
                f"LinkedIn image upload error {upload_response.status_code}\n{upload_response.text}"
            )


    # ---------------- REQUEST: POST WITH OR WITHOUT MEDIA ----------------
    url = "https://api.linkedin.com/rest/posts"


    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


    payload = {
        "author": f"urn:li:person:{person_urn}",
        "commentary": final_post,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }


    if image_urn:
        payload["content"] = {
            "media": {
                "id": image_urn,
                }
        }


    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,
    )


    # Duplicate-post handling
    if response.status_code == 422:
        try:
            error_data = response.json()
            if any(
                error.get("code") == "DUPLICATE_POST"
                for error in error_data.get("errorDetails", {}).get("inputErrors", [])
            ):
                raise RuntimeError(
                    "LinkedIn rejected this post because the same content "
                    "has already been published. Please change the post "
                    "content and try again."
                )
        except ValueError:
            pass


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