import json
import re
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

try:
    import streamlit as st
except ImportError:
    st = None


def safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def get_openai_api_key():
    if st is not None:
        try:
            return st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass
    return None


def get_openai_client():
    api_key = get_openai_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in Streamlit secrets")
    return OpenAI(api_key=api_key)


def duckduckgo_search(query: str, max_results: int = 3) -> List[Dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://html.duckduckgo.com/html/"
    response = requests.post(url, data={"q": query}, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for a in soup.select("a.result__a")[:max_results]:
        title = safe_text(a.get_text(" ", strip=True))
        href = safe_text(a.get("href"))
        if title and href:
            results.append({"title": title, "url": href})

    return results


def fetch_page_text(url: str, max_chars: int = 1200) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        return text[:max_chars]
    except Exception:
        return ""


def build_web_context(company_data: dict, post_data: dict) -> str:
    company_name = safe_text(company_data.get("company"))
    industry = safe_text(company_data.get("industry"))
    title = safe_text(post_data.get("title"))
    key_points = safe_text(post_data.get("key_points"))
    audience = safe_text(post_data.get("audience"))

    queries = [
        f"{company_name} {industry}".strip(),
        f"{company_name} latest news".strip(),
        f"{company_name} {title} {key_points} {audience}".strip(),
    ]

    blocks = []

    for query in queries:
        if not query:
            continue

        try:
            results = duckduckgo_search(query, max_results=2)
        except Exception:
            continue

        if not results:
            continue

        blocks.append(f"Search query: {query}")

        for item in results:
            result_title = safe_text(item.get("title"))
            url = safe_text(item.get("url"))
            page_text = fetch_page_text(url, max_chars=1000)
            if page_text:
                blocks.append(
                    f"Title: {result_title}\nURL: {url}\nExcerpt: {page_text[:600]}"
                )

    return "\n\n".join(blocks)[:5000]


def build_prompt(
    company_data: dict,
    post_data: dict,
    platform: str,
    tone: str,
    web_context: str,
) -> str:
    company_name = safe_text(company_data.get("company"))
    industry = safe_text(company_data.get("industry"))
    about = safe_text(company_data.get("about"))
    brand_voice = safe_text(company_data.get("brand_voice"))

    post_type = safe_text(post_data.get("post_type"))
    title = safe_text(post_data.get("title"))
    body = safe_text(post_data.get("body"))
    key_points = safe_text(post_data.get("key_points"))
    audience = safe_text(post_data.get("audience"))
    media_type = safe_text(post_data.get("media_type"))
    media_file_name = safe_text(post_data.get("media_file_name"))
    media_note = safe_text(post_data.get("media_note"))
    user_prompt = safe_text(post_data.get("user_prompt"))

    return f"""
You are a senior content strategist and social media copywriter.

Write content that matches the user's intent, not generic marketing filler.
Use the company context, the user prompt, and web context only to support and improve the final result.
Do not invent claims or numbers.

COMPANY
Name: {company_name}
Industry: {industry}
About: {about}
Brand voice: {brand_voice}

USER INTENT
User prompt: {user_prompt}
Post type: {post_type}
Title: {title}
Body: {body}
Key points: {key_points}
Audience: {audience}

MEDIA
Media type: {media_type}
Media file name: {media_file_name}
Media note: {media_note}

PLATFORM
Platform: {platform}
Tone: {tone}

WEB CONTEXT
{web_context if web_context else "No external web context available."}

OUTPUT RULES
- hook: short opening line
- main_post: polished platform-ready post
- caption: short support caption
- cta: one clear call to action
- hashtags: 4 to 8 relevant hashtags in one string
- Keep it specific, natural, and aligned to the user’s intent
- If the prompt is about internship, job, visit, event, or launch, reflect that directly
- If web context exists, use it to enrich style and relevance, not to make unsupported claims
- Return valid JSON only
""".strip()


def generate_social_content(
    company_data: dict,
    post_data: dict,
    platform: str,
    tone: str,
    use_web_context: bool = True,
) -> dict:
    client = get_openai_client()

    web_context = ""
    if use_web_context:
        try:
            web_context = build_web_context(company_data, post_data)
        except Exception:
            web_context = ""

    schema = {
        "type": "object",
        "properties": {
            "hook": {"type": "string"},
            "main_post": {"type": "string"},
            "caption": {"type": "string"},
            "cta": {"type": "string"},
            "hashtags": {"type": "string"},
        },
        "required": ["hook", "main_post", "caption", "cta", "hashtags"],
        "additionalProperties": False,
    }

    prompt = build_prompt(
        company_data=company_data,
        post_data=post_data,
        platform=platform,
        tone=tone,
        web_context=web_context,
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON that matches the schema.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "social_content_package",
                "schema": schema,
                "strict": True,
            },
        },
        temperature=0.7,
    )

    parsed = json.loads(response.choices[0].message.content)

    return {
        "hook": safe_text(parsed.get("hook")),
        "main_post": safe_text(parsed.get("main_post")),
        "caption": safe_text(parsed.get("caption")),
        "cta": safe_text(parsed.get("cta")),
        "hashtags": safe_text(parsed.get("hashtags")),
    }