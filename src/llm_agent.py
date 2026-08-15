import json
import re
from typing import List, Dict
import os
import requests

from groq import Groq

from google import genai
from google.genai import types

from bs4 import BeautifulSoup

from openai import OpenAI  

from dotenv import load_dotenv
load_dotenv()

try:
    import streamlit as st
except ImportError:
    st = None


def safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def get_groq_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)

def get_gemini_client() -> genai.Client | None:
    api_key = get_gemini_api_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


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
    """
    Generate a structured social content package for the given company + post,
    tailored to a specific platform and tone, optionally using web context.

    Returns a dict with keys: hook, main_post, caption, cta, hashtags.
    """

    client = get_groq_client()
    if client is None:
        # Fallback: if no Groq key, return a simple template rather than crashing
        return {
            "hook": f"{company_data.get('company', '')}: {post_data.get('title', '')}",
            "main_post": (
                f"We’re pleased to share an update from {company_data.get('company', 'the company')}.\n\n"
                f"{post_data.get('update', post_data.get('title', ''))}\n\n"
                "What are your thoughts? Share them in the comments."
            ),
            "caption": f"{company_data.get('company', '')} | {post_data.get('title', '')}",
            "cta": "What are your thoughts? Share them in the comments.",
            "hashtags": "#LinkedIn #BusinessUpdate #Innovation #Growth",
        }

    web_context = ""
    if use_web_context:
        try:
            web_context = build_web_context(company_data, post_data)
        except Exception:
            web_context = ""

    prompt = build_prompt(
        company_data=company_data,
        post_data=post_data,
        platform=platform,
        tone=tone,
        web_context=web_context,
    )

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

    schema_instructions = (
        "Return ONLY valid JSON with exactly these keys: "
        "hook (string), main_post (string), caption (string), "
        "cta (string), hashtags (string). "
        "Do not include markdown formatting, code fences, or any extra text."
    )

    full_prompt = f"{schema_instructions}\n\n{prompt}"

    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # or another free Groq model [214][225]
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON that matches the schema.",
            },
            {"role": "user", "content": full_prompt},
        ],
        temperature=0.7,
    )

    raw_content = chat_completion.choices[0].message.content
    parsed = json.loads(raw_content)

    return {
        "hook": safe_text(parsed.get("hook")),
        "main_post": safe_text(parsed.get("main_post")),
        "caption": safe_text(parsed.get("caption")),
        "cta": safe_text(parsed.get("cta")),
        "hashtags": safe_text(parsed.get("hashtags")),
    }