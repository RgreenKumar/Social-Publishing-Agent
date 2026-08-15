import os
import json
import re
from typing import Optional, Any, List, Dict

import requests
from bs4 import BeautifulSoup
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


# --------- LLM / Client Setup ---------


def get_groq_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


# Choose a Groq model for research and generation
RESEARCH_MODEL = os.getenv("GROQ_RESEARCH_MODEL", "llama-3.3-70b-versatile")


# --------- Utility Functions ---------


def safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_platform(platform: str) -> str:
    if not platform:
        return "linkedin"

    p = platform.strip().lower()

    aliases = {
        "linkedin": "linkedin",
        "instagram": "instagram",
        "facebook": "facebook",
        "x": "x",
        "twitter": "x",
        "twitter/x": "x",
        "x.com": "x",
    }

    return aliases.get(p, p)


def _walk_nodes(obj: Any):
    """
    Recursively walk dict/list structures.
    """
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_nodes(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_nodes(item)


# --------- Web Search Helpers ---------


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


def extract_web_sources_from_payload(payload: dict) -> list[dict]:
    """
    Extract sources from a Groq chat completion payload, if any were
    encoded in the response. For now, we treat any URLs mentioned in
    the model's JSON output as sources.
    """
    sources = []
    seen_urls = set()

    for node in _walk_nodes(payload):
        if not isinstance(node, dict):
            continue

        url = node.get("url")
        title = node.get("title")

        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append(
                {
                    "title": title or "Web source",
                    "url": url,
                }
            )

    return sources


# --------- Platform Guidance ---------


PLATFORM_GUIDANCE = {
    "linkedin": """
Use a professional but human tone.
Begin with a strong opening line.
Use short paragraphs.
Highlight business value, achievement, or insight.
Finish with a meaningful call to action.
Use only a few relevant hashtags.
""",
    "instagram": """
Write visually engaging and conversational content.
Use a strong caption opening.
Connect the caption clearly to the uploaded or planned media.
Use relevant emojis only where natural.
Finish with an engagement question or call to action.
""",
    "facebook": """
Use an accessible, community-friendly tone.
Explain the update clearly.
Encourage comments, reactions, or visits.
Avoid sounding overly corporate.
""",
    "x": """
Be direct and concise.
Lead with the most important message.
Avoid unnecessary introduction.
Use only highly relevant hashtags.
""",
}


# --------- Research and Generation ---------


def research_company(
    company: str,
    user_prompt: str,
    platform: str,
    company_url: Optional[str] = None,
) -> dict:
    """
    Searches the web (via DuckDuckGo scraping) and produces a factual company report,
    then uses Groq to summarize findings in a structured way.
    """

    client = get_groq_client()
    platform_key = normalize_platform(platform)

    if client is None:
        return {
            "report": "Research is temporarily unavailable (no GROQ_API_KEY configured).",
            "sources": [],
            "platform": platform_key,
        }

    company_reference = company.strip()
    if company_url:
        company_reference += f"\nCompany website supplied by user: {company_url.strip()}"

    # Use DuckDuckGo search to gather basic context & sources
    queries = [
        f"{company} latest news",
        f"{company} official website",
        user_prompt,
    ]

    context_blocks = []
    sources = []

    for q in queries:
        try:
            results = duckduckgo_search(q, max_results=2)
        except Exception:
            continue

        for item in results:
            title = safe_text(item.get("title"))
            url = safe_text(item.get("url"))
            if not url:
                continue
            page_text = fetch_page_text(url, max_chars=800)
            if page_text:
                context_blocks.append(
                    f"Query: {q}\nTitle: {title}\nURL: {url}\nExcerpt: {page_text}"
                )
                sources.append({"title": title or "Web source", "url": url})

    web_context = "\n\n".join(context_blocks)[:4000] or "No external web context available."

    research_prompt = f"""
You are a research assistant helping a social publishing agent.

Company:
{company_reference}

Target platform:
{platform}

User's requested post:
{user_prompt}

Collected web context:
{web_context}

Research requirements:
1. Confirm that this is the correct company (if possible).
2. Prefer the company's official website and official announcements.
3. Find recent and relevant information related to the user's request.
4. Identify the company's industry, products or services, and audience.
5. Do not invent achievements, partnerships, dates, statistics, or claims.
6. Clearly state when information cannot be verified.
7. Produce a concise research report that a social-media copywriter can use.
8. Separate verified facts from suggested creative angles.
9. Return JSON with keys:
   - summary: textual research summary
   - bullets: list of key bullet points
"""

    chat_completion = client.chat.completions.create(
        model=RESEARCH_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON with keys 'summary' and 'bullets'.",
            },
            {"role": "user", "content": research_prompt},
        ],
        temperature=0.2,
    )

    raw = chat_completion.choices[0].message.content

    try:
        data = json.loads(raw)
        summary = safe_text(data.get("summary"))
        bullets = data.get("bullets") or []
        bullets = [safe_text(b) for b in bullets if b]
        report_text = summary + "\n\n" + "\n".join(f"- {b}" for b in bullets)
    except Exception:
        # Fallback if model didn't follow JSON perfectly
        report_text = raw.strip()

    return {
        "report": report_text,
        "sources": sources,
        "platform": platform_key,
    }


def generate_platform_post(
    company: str,
    platform: str,
    tone: str,
    user_prompt: str,
    research_report: str,
    media_context: Optional[str] = None,
) -> str:
    """
    Generates the final platform-specific draft using verified research and
    the user's instructions, using Groq instead of OpenAI.
    """

    client = get_groq_client()
    platform_key = normalize_platform(platform)

    if client is None:
        return "Publishing agent is temporarily unavailable (no GROQ_API_KEY configured)."

    platform_rules = PLATFORM_GUIDANCE.get(
        platform_key,
        "Write clearly for the selected social platform.",
    )

    media_context = media_context or "No media information was provided."

    generation_prompt = f"""
You are a social publishing agent.

Create one polished post using the information below.

Company:
{company}

Platform:
{platform}

Tone:
{tone}

User instructions:
{user_prompt}

Media context:
{media_context}

Verified research:
{research_report}

Platform writing guidance:
{platform_rules}

Important rules:
- Follow the user's requested purpose.
- Adapt the structure and writing style to the selected platform.
- Use only facts supported by the research.
- Do not invent statistics, dates, awards, partnerships, or claims.
- Connect the copy naturally to the image or video context.
- Do not include research notes inside the final post.
- Return only the ready-to-publish social-media content.
"""

    chat_completion = client.chat.completions.create(
        model=RESEARCH_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a social publishing agent. Return only the final post text.",
            },
            {"role": "user", "content": generation_prompt},
        ],
        temperature=0.4,
    )
    return (chat_completion.choices[0].message.content or "").strip()