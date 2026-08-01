from src.platform_adapters.linkedin_adapter import publish_linkedin_post
from src.platform_adapters.twitter_adapter import publish_twitter_post
from src.platform_adapters.facebook_adapter import publish_facebook_post
from src.platform_adapters.instagram_adapter import publish_instagram_post


PLATFORM_ALIASES = {
    "linkedin": "linkedin",
    "twitter": "twitter",
    "twitter/x": "twitter",
    "x": "twitter",
    "x.com": "twitter",
    "facebook": "facebook",
    "instagram": "instagram",
}


def normalize_platform(platform: str) -> str:
    if not platform:
        raise ValueError("Platform is required.")

    key = platform.strip().lower()
    return PLATFORM_ALIASES.get(key, key)


def normalize_content(content):
    """
    Accepts either a string draft or a dict draft and returns a usable text draft.
    """
    if content is None:
        return ""

    if isinstance(content, dict):
        return (
            content.get("main_post")
            or content.get("body")
            or content.get("text")
            or content.get("caption")
            or str(content)
        )

    return str(content)


def publish_post(platform, content, post_data=None, company_data=None):
    """
    Routes publishing to the correct platform adapter.
    Returns a consistent dictionary response.
    """
    normalized_platform = normalize_platform(platform)
    text_content = normalize_content(content)

    if normalized_platform == "linkedin":
        return publish_linkedin_post(
            text_content,
            post_data,
            company_data,
        )

    elif normalized_platform == "twitter":
        return publish_twitter_post(
            text_content,
            post_data,
            company_data,
        )

    elif normalized_platform == "facebook":
        return publish_facebook_post(
            text_content,
            post_data,
            company_data,
        )

    elif normalized_platform == "instagram":
        return publish_instagram_post(
            text_content,
            post_data,
            company_data,
        )

    else:
        raise ValueError(f"Unsupported platform: {platform}")