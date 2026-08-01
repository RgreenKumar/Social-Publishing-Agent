from src.data_loader import load_company_updates

try:
    from src.llm_agent import generate_social_content
except Exception:
    generate_social_content = None


def build_content_brief(update: dict, platform: str, tone: str, user_prompt: str = "") -> dict:
    return {
        "company": update.get("company", ""),
        "title": update.get("title", ""),
        "body": update.get("body", ""),
        "content_type": update.get("type", ""),
        "platform": platform.lower(),
        "tone": tone.lower(),
        "user_prompt": (user_prompt or "").strip(),
    }


def generate_fallback_content(update: dict, platform: str, tone: str, user_prompt: str = "") -> dict:
    company = update.get("company", "")
    title = update.get("title", "")
    body = update.get("body", "")
    content_type = update.get("type", "")

    platform = (platform or "").lower()
    tone = (tone or "").lower()
    user_prompt = (user_prompt or "").strip()

    if tone == "professional":
        tone_prefix = "We’re pleased to share"
        cta = "What are your thoughts? Share them in the comments."
    elif tone == "friendly":
        tone_prefix = "Excited to share"
        cta = "We’d love to hear what you think."
    else:
        tone_prefix = "We would like to announce"
        cta = "Please share your feedback."

    hook = f"{company}: {user_prompt[:70]}" if user_prompt else f"{company}: {title}"

    if platform == "linkedin":
        main_post = (
            f"{tone_prefix} an important update from {company}.\n\n"
            f"{body}\n\n"
            f"This highlights another step forward in {content_type.lower()}.\n\n"
            f"{cta}"
        )
        caption = f"{company} | {title}"
        hashtags = "#LinkedIn #BusinessUpdate #Innovation #Growth"

    elif platform == "twitter":
        main_post = f"{company}: {title}\n\n{body[:220].rstrip()}"
        caption = f"{company} update"
        hashtags = "#Update #Innovation #Tech"

    elif platform == "facebook":
        main_post = (
            f"{tone_prefix} an update from {company}.\n\n"
            f"{body}\n\n"
            f"Stay connected for more updates."
        )
        caption = title
        hashtags = "#Business #Update #Community"

    elif platform == "instagram":
        main_post = (
            f"{tone_prefix} something new at {company}.\n\n"
            f"{body}\n\n"
            f"More exciting updates ahead."
        )
        caption = f"{title} — a quick look at what’s happening at {company}."
        hashtags = "#Instagram #BrandUpdate #Innovation #NewLaunch"

    else:
        main_post = body
        caption = title
        hashtags = "#Update"

    return {
        "hook": hook,
        "main_post": main_post,
        "caption": caption,
        "cta": cta,
        "hashtags": hashtags,
    }


def create_draft(update_id, platform, tone, user_prompt=""):
    updates_df = load_company_updates()
    row = updates_df[updates_df["id"] == update_id].iloc[0]

    update = {
        "id": int(row["id"]),
        "company": row["company"],
        "title": row["title"],
        "type": row["type"],
        "body": row["body"],
    }

    brief = build_content_brief(update, platform, tone, user_prompt)

    if generate_social_content is not None:
        try:
            content_package = generate_social_content(
                company_data=update,
                post_data=brief,
                platform=platform,
                tone=tone,
                use_web_context=True,
            )
            return update, content_package
        except Exception:
            pass

    content_package = generate_fallback_content(update, platform, tone, user_prompt)
    return update, content_package