import os
from typing import Optional, Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# The docs recommend gpt-5.5 for the web-search path.
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.5")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

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
    "twitter": """
Be direct and concise.
Lead with the most important message.
Avoid unnecessary introduction.
Use only highly relevant hashtags.
""",
}


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


def extract_web_sources(response) -> list[dict]:
    """
    Extract sources from OpenAI Responses output.
    Handles both:
    - web_search_call.action.sources
    - url_citation annotations in the response output
    """
    sources = []
    seen_urls = set()

    try:
        payload = response.model_dump()
    except Exception:
        return sources

    for node in _walk_nodes(payload):
        if not isinstance(node, dict):
            continue

        node_type = node.get("type")

        # Case 1: web_search_call action sources
        if node_type == "web_search_call":
            action = node.get("action") or {}
            for source in action.get("sources", []) or []:
                if not isinstance(source, dict):
                    continue
                url = source.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                sources.append(
                    {
                        "title": source.get("title", "Web source"),
                        "url": url,
                    }
                )

        # Case 2: citation annotations
        if node_type == "url_citation":
            url = node.get("url")
            if not url:
                citation = node.get("url_citation")
                if isinstance(citation, dict):
                    url = citation.get("url")

            if not url or url in seen_urls:
                continue

            title = node.get("title")
            if not title:
                citation = node.get("url_citation")
                if isinstance(citation, dict):
                    title = citation.get("title")

            seen_urls.add(url)
            sources.append(
                {
                    "title": title or "Web source",
                    "url": url,
                }
            )

    return sources


def research_company(
    company: str,
    user_prompt: str,
    platform: str,
    company_url: Optional[str] = None,
) -> dict:
    """
    Searches the web and produces a factual company report.
    """

    platform_key = normalize_platform(platform)

    company_reference = company.strip()
    if company_url:
        company_reference += f"\nCompany website supplied by user: {company_url.strip()}"

    research_prompt = f"""
Research the company below for the purpose of creating a social-media post.

Company:
{company_reference}

Target platform:
{platform}

User's requested post:
{user_prompt}

Research requirements:
1. Confirm that this is the correct company.
2. Prefer the company's official website and official announcements.
3. Find recent and relevant information related to the user's request.
4. Identify the company's industry, products or services, and audience.
5. Do not invent achievements, partnerships, dates, statistics, or claims.
6. Clearly state when information cannot be verified.
7. Produce a concise research report that a social-media copywriter can use.
8. Separate verified facts from suggested creative angles.
9. Return a research summary with clear bullets and source-backed notes.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        tools=[{"type": "web_search"}],
        tool_choice="required",
        include=["web_search_call.action.sources"],
        input=research_prompt,
    )

    report_text = getattr(response, "output_text", "") or ""

    return {
        "report": report_text.strip(),
        "sources": extract_web_sources(response),
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
    Generates the final platform-specific draft using
    verified research and the user's instructions.
    """

    platform_key = normalize_platform(platform)

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
    response = client.responses.create(
        model=MODEL_NAME,
        input=generation_prompt,
    )

    return (getattr(response, "output_text", "") or "").strip()