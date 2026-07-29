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
        raise ValueError("OPENAI_API_KEY not found in .streamlit/secrets.toml")
    return OpenAI(api_key=api_key)


def safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def extract_domain(url: str) -> str:
    url = safe_text(url)
    url = re.sub(r"^https?://", "", url)
    url = url.split("/")[0]
    return url.strip()


def duckduckgo_search(query: str, max_results: int = 5) -> List[Dict]:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query}

    response = requests.post(url, data=data, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for a in soup.select("a.result__a")[:max_results]:
        title = safe_text(a.get_text(" ", strip=True))
        href = a.get("href", "").strip()
        if title and href:
            results.append({"title": title, "url": href})

    return results


def fetch_page_text(url: str, max_chars: int = 2500) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars]
    except Exception:
        return ""


def build_web_context(company_data: dict, post_data: dict) -> str:
    company_name = safe_text(company_data.get("company"))
    industry = safe_text(company_data.get("industry"))
    post_type = safe_text(post_data.get("post_type"))
    title = safe_text(post_data.get("title"))

    search_queries = [
        f"{company_name} company {industry}".strip(),
        f"{company_name} latest news".strip(),
        f"{company_name} {post_type} {title}".strip(),
    ]

    context_parts = []

    for query in search_queries:
        if not query:
            continue

        try:
            results = duckduckgo_search(query, max_results=3)
        except Exception:
            continue

        if not results:
            continue

        context_parts.append(f"Search query: {query}")

        for item in results[:2]:
            title_text = safe_text(item.get("title"))
            url = safe_text(item.get("url"))
            page_text = fetch_page_text(url, max_chars=1500)

            snippet = page_text[:700] if page_text else ""
            block = f"Title: {title_text}\nURL: {url}\nContent: {snippet}"
            context_parts.append(block)

    return "\n\n".join(context_parts)[:6000]


def build_prompt(company_data: dict, post_data: dict, platform: str, tone: str, use_web_context: bool, web_context: str) -> str:
    company_name = safe_text(company_data.get("company"))
    industry = safe_text(company_data.get("industry"))
    company_about = safe_text(company_data.get("about"))
    brand_voice = safe_text(company_data.get("brand_voice"))

    post_type = safe_text(post_data.get("post_type"))
    post_title = safe_text(post_data.get("title"))
    post_body = safe_text(post_data.get("body"))
    key_points = safe_text(post_data.get("key_points"))
    audience = safe_text(post_data.get("audience"))
    media_type = safe_text(post_data.get("media_type"))
    media_file_name = safe_text(post_data.get("media_file_name"))
    media_note = safe_text(post_data.get("media_note"))

    return f"""
You are an expert social media content strategist.

Your job:
1. Understand the company identity.
2. Understand the current post/update the user wants to publish.
3. If web context is available, use it to ground the company context and recent relevance.
4. Generate polished content that feels specific to this company and this update.
5. Do not sound generic, repetitive, or template-like.
6. Do not invent unsupported claims. If web context is weak, rely more on user-provided data.
7. Keep the company identity, post topic, and audience aligned.

INPUTS

Company name: {company_name}
Industry: {industry}
Company about: {company_about}
Brand voice: {brand_voice}

Post type: {post_type}
Post title: {post_title}
Post details: {post_body}
Key points: {key_points}
Audience: {audience}

Media type: {media_type}
Media file name: {media_file_name}
Media note: {media_note}

Platform: {platform}
Tone: {tone}
Use web context: {use_web_context}

WEB CONTEXT
{web_context if web_context else "No external web context available."}

OUTPUT RULES
- hook: short, sharp opening line
- main_post: platform-ready main body, specific and natural
- caption: concise support line
- cta: one clear call to action
- hashtags: one string with 4 to 8 relevant hashtags
- Avoid fake statistics, fake achievements, and unverifiable claims
- Keep the writing fresh and brand-aligned
- If the post is about a launch, event, hiring, milestone, or thought leadership topic, reflect that clearly
- If media is mentioned, lightly align the copy with that media context
- Do not include markdown code fences
- Return JSON only
"""


def generate_social_content(company_data: dict, post_data: dict, platform: str, tone: str, use_web_context: bool = True) -> dict:
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
            "hashtags": {"type": "string"}
        },
        "required": ["hook", "main_post", "caption", "cta", "hashtags"],
        "additionalProperties": False
    }

    prompt = build_prompt(
        company_data=company_data,
        post_data=post_data,
        platform=platform,
        tone=tone,
        use_web_context=use_web_context,
        web_context=web_context,
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Return valid JSON only. Follow the schema exactly."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "social_content_package",
                "schema": schema,
                "strict": True
            }
        },
        temperature=0.7,
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)

    return {
        "hook": safe_text(parsed.get("hook")),
        "main_post": safe_text(parsed.get("main_post")),
        "caption": safe_text(parsed.get("caption")),
        "cta": safe_text(parsed.get("cta")),
        "hashtags": safe_text(parsed.get("hashtags")),
    }