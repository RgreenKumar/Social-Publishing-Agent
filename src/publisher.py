from config import PUBLISH_MODE
from src.platform_adapters.linkedin_adapter import publish_to_linkedin

def publish_post(platform, content):
    if PUBLISH_MODE == "mock":
        return {"success": True, "message": f"Mock published to {platform}"}

    if platform == "LinkedIn":
        return publish_to_linkedin(content)

    return {"success": False, "message": f"Publishing not configured for {platform}"}