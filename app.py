
import streamlit as st
import pandas as pd

from datetime import datetime, time
from typing import Any, Dict, List, Optional

from src.data_loader import load_company_updates
from src.workflow import create_draft
from src.publisher import publish_post

try:
    from src.research_agent import research_company, generate_platform_post
    HAS_RESEARCH_AGENT = True
except Exception:
    HAS_RESEARCH_AGENT = False
    research_company = None
    generate_platform_post = None

from src.storage import (
    init_db,
    save_post,
    load_posts,
    update_draft,
    update_post_status,
    schedule_post,
    get_statistics,
)
# Page setup

st.set_page_config(
    page_title="AI Social Publishing Agent",
    page_icon="🚀",
    layout="wide",
)

init_db()

# Constants

PLATFORM_LABEL_TO_KEY = {
    "LinkedIn": "linkedin",
    "Twitter/X": "twitter",
    "Facebook": "facebook",
    "Instagram": "instagram",
}

PLATFORM_KEY_TO_LABEL = {v: k for k, v in PLATFORM_LABEL_TO_KEY.items()}

RECOMMENDED_POSTING_TIMES = {
    "LinkedIn": {
        "label": "Tue–Thu • 9:00–11:00 AM",
        "time": time(9, 30),
        "reason": "Professional audiences are usually active mid-morning on weekdays.",
    },
    "Twitter/X": {
        "label": "Mon–Fri • 8:00–10:00 AM",
        "time": time(8, 30),
        "reason": "Early weekday mornings often perform well for short updates.",
    },
    "Facebook": {
        "label": "Mon–Fri • 1:00–3:00 PM",
        "time": time(13, 30),
        "reason": "Midday posts usually get better community engagement.",
    },
    "Instagram": {
        "label": "Mon–Fri • 6:00–8:00 PM",
        "time": time(18, 30),
        "reason": "Evening hours typically work well for visual content.",
    },
}

TONE_OPTIONS = [
    "Professional",
    "Friendly",
    "Formal",
    "Excited",
    "Marketing",
    "Neutral",
]

WORKFLOW_OPTIONS = [
    "Existing Company Update",
    "Manual Company Research",
]

MEDIA_OPTIONS = [
    "None",
    "Image",
    "Video",
]
# Session state

DEFAULT_SESSION = {
    "current_update": None,
    "current_draft": None,
    "research_report": "",
    "research_sources": [],
    "saved_post_id": None,
    "selected_platform": "LinkedIn",
    "selected_tone": "Professional",
    "company_mode": "Manual Company Research",
    "company_input": "",
    "company_url": "",
    "title_input": "",
    "user_prompt": "",
    "media_notes": "",
    "existing_prompt": "",
}

for key, value in DEFAULT_SESSION.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Helpers

def platform_to_key(platform_label: str) -> str:
    return PLATFORM_LABEL_TO_KEY.get(platform_label, (platform_label or "").lower())


def platform_to_label(platform_key: str) -> str:
    return PLATFORM_KEY_TO_LABEL.get(platform_key, platform_key.title() if platform_key else "")

def pretty_status(status: Any) -> str:
    if status is None:
        return ""
    status_text = str(status).strip().lower()
    icons = {
        "draft": "📝 Draft",
        "approved": "✅ Approved",
        "needs_revision": "🟠 Needs Revision",
        "scheduled": "📅 Scheduled",
        "published": "🟢 Published",
        "failed": "❌ Failed",
    }
    return icons.get(status_text, str(status))

def normalize_draft_text(draft: Any) -> str:
    if draft is None:
        return ""

    if isinstance(draft, str):
        return draft

    if isinstance(draft, dict):
        return (
            draft.get("main_post")
            or draft.get("body")
            or draft.get("text")
            or draft.get("caption")
            or draft.get("hook")
            or str(draft)
        )

    return str(draft)

def get_recommendation(platform_label: str) -> Dict[str, Any]:
    return RECOMMENDED_POSTING_TIMES.get(
        platform_label,
        {
            "label": "Morning • 9:00–10:00 AM",
            "time": time(9, 0),
            "reason": "Morning posts are usually a safe default for business content.",
        },
    )


def show_media_preview(uploaded_file, media_type: str) -> None:
    if uploaded_file is None:
        return

    st.subheader("Media Preview")

    if media_type == "Image":
        st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
    elif media_type == "Video":
        st.video(uploaded_file)
    else:
        st.info("No preview available for this media type.")


def render_company_update(update: Dict[str, Any]) -> None:
    st.markdown("### Selected Company Update")
    st.write(f"**Company:** {update.get('company', '')}")
    st.write(f"**Title:** {update.get('title', '')}")
    st.write(f"**Type:** {update.get('type', '')}")
    st.write("**Body:**")
    st.write(update.get("body", ""))


def render_sources(sources: List[Dict[str, Any]]) -> None:
    if not sources:
        st.info("No source links were returned.")
        return

    st.markdown("### Sources")
    for source in sources:
        title = source.get("title", "Source")
        url = source.get("url", "")
        if url:
            st.markdown(f"- [{title}]({url})")


def fallback_manual_draft(
    company: str,
    platform_label: str,
    tone: str,
    user_prompt: str,
    research_report: str = "",
    media_context: str = "",
) -> str:
    tone_value = (tone or "").strip().lower()
    platform_key = platform_to_key(platform_label)

    openers = {
        "professional": "We’re pleased to share",
        "friendly": "Excited to share",
        "formal": "We are pleased to announce",
        "excited": "Excited to share",
        "marketing": "Introducing",
        "neutral": "Here is an update from",
    }

    ctas = {
        "linkedin": "What are your thoughts? Share them in the comments.",
        "twitter": "Stay tuned for more updates.",
        "facebook": "We would love to hear your thoughts below.",
        "instagram": "Tell us what you think in the comments.",
    }

    hashtags = {
        "linkedin": "#LinkedIn #BusinessUpdate #Innovation #Growth",
        "twitter": "#Update #Innovation #Tech",
        "facebook": "#Business #Update #Community",
        "instagram": "#Instagram #BrandUpdate #Innovation #NewLaunch",
    }

    opener = openers.get(tone_value, "We would like to share")
    cta = ctas.get(platform_key, "Share your thoughts with us.")
    tag_line = hashtags.get(platform_key, "#Update")

    parts = [
        f"{opener} an update from {company}.",
    ]

    if user_prompt.strip():
        parts.append(user_prompt.strip())

    if research_report.strip():
        parts.append(research_report.strip())

    if media_context.strip():
        parts.append(media_context.strip())

    parts.append(cta)
    parts.append(tag_line)

    return "\n\n".join(parts)


def build_save_kwargs(
    current_update: Dict[str, Any],
    edited_draft: str,
    status: str,
    platform_label: str,
    tone: str,
    research_report: str,
    research_sources: List[Dict[str, Any]],
    media_type: str,
    media_name: Optional[str],
    media_notes: str,
    company_mode: str,
    user_prompt: str,
    company_url: str,
) -> Dict[str, Any]:
    platform_key = platform_to_key(platform_label)

    return {
        "update_id": current_update.get("id"),
        "company": current_update.get("company", ""),
        "title": current_update.get("title", ""),
        "platform": platform_key,
        "draft": edited_draft,
        "status": status,
        "publish_mode": "manual_research"
        if company_mode == "Manual Company Research"
        else "existing_update",
        "tone": tone,
        "user_prompt": user_prompt,
        "company_url": company_url,
        "research_summary": research_report,
        "source_urls": research_sources,
        "media_name": media_name,
        "media_type": media_type if media_type != "None" else None,
        "media_notes": media_notes,
    }


def ensure_current_context() -> bool:
    return bool(st.session_state.get("current_update") and st.session_state.get("current_draft"))

# Page header

st.title("🤖 AI Social Publishing Agent")
st.caption("Generate, research, edit, save, schedule, and publish social posts.")

# Sidebar

with st.sidebar:
    st.header("Settings")

    st.session_state["company_mode"] = st.radio(
        "Company Source",
        WORKFLOW_OPTIONS,
        index=WORKFLOW_OPTIONS.index(st.session_state.get("company_mode", "Manual Company Research"))
        if st.session_state.get("company_mode", "Manual Company Research") in WORKFLOW_OPTIONS
        else 0,
    )

    selected_platform = st.selectbox(
        "Platform",
        list(PLATFORM_LABEL_TO_KEY.keys()),
        index=list(PLATFORM_LABEL_TO_KEY.keys()).index(
            st.session_state.get("selected_platform", "LinkedIn")
        )
        if st.session_state.get("selected_platform", "LinkedIn") in PLATFORM_LABEL_TO_KEY
        else 0,
    )

    selected_tone = st.selectbox(
        "Tone",
        TONE_OPTIONS,
        index=TONE_OPTIONS.index(st.session_state.get("selected_tone", "Professional"))
        if st.session_state.get("selected_tone", "Professional") in TONE_OPTIONS
        else 0,
    )

    st.session_state["selected_platform"] = selected_platform
    st.session_state["selected_tone"] = selected_tone

    st.divider()

    media_type = st.selectbox("Media Type", MEDIA_OPTIONS)
    uploaded_media = None
    if media_type != "None":
        uploaded_media = st.file_uploader(
            "Upload media",
            type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "avi"],
        )

    if uploaded_media is not None:
        show_media_preview(uploaded_media, media_type)

# Dashboard metrics

stats_df = get_statistics()
counts = {"draft": 0, "scheduled": 0, "published": 0, "failed": 0}

if not stats_df.empty and "status" in stats_df.columns and "total" in stats_df.columns:
    for _, row in stats_df.iterrows():
        counts[str(row["status"]).strip().lower()] = int(row["total"])

all_posts_df = load_posts()
total_posts = int(len(all_posts_df)) if isinstance(all_posts_df, pd.DataFrame) else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Posts", total_posts)
c2.metric("Drafts", counts.get("draft", 0))
c3.metric("Scheduled", counts.get("scheduled", 0))
c4.metric("Published", counts.get("published", 0))
c5.metric("Failed", counts.get("failed", 0))

st.markdown("---")

# Tabs

dashboard_tab, create_tab, research_tab, preview_tab, history_tab, publish_tab = st.tabs(
    [
        "📊 Dashboard",
        "✍ Create Post",
        "🔍 Research",
        "📝 Preview",
        "📚 History",
        "🚀 Publish",
    ]
)

# Dashboard Tab

with dashboard_tab:
    st.subheader("Overview")

    st.write(
        "Use the Create Post tab to generate drafts using either your existing company updates or manual web research."
    )

    st.markdown("### Recommended Posting Time")
    recommendation = get_recommendation(st.session_state["selected_platform"])
    st.success(
        f"{st.session_state['selected_platform']}: {recommendation['label']}"
    )
    st.caption(recommendation["reason"])

    st.markdown("### Recent Posts")
    recent_df = load_posts(limit=5)
    if recent_df.empty:
        st.info("No posts yet.")
    else:
        recent_display = recent_df.copy()
        if "platform" in recent_display.columns:
            recent_display["platform"] = recent_display["platform"].apply(platform_to_label)
        if "status" in recent_display.columns:
            recent_display["status"] = recent_display["status"].apply(pretty_status)
        columns_to_show = [
            col for col in [
                "id", "timestamp", "company", "title", "platform", "status", "published_url"
            ] if col in recent_display.columns
        ]
        st.dataframe(
            recent_display[columns_to_show],
            use_container_width=True,
            hide_index=True,
        )

# Create Tab

with create_tab:
    st.subheader("Create a Draft")

    if st.session_state["company_mode"] == "Existing Company Update":
        updates_df = load_company_updates()

        if updates_df.empty:
            st.error("No company updates found in data/company_updates.csv.")
        else:
            update_options = [
                f"{int(row.id)} | {row.company} | {row.title}"
                for _, row in updates_df.iterrows()
            ]

            selected_index = st.selectbox(
                "Choose a company update",
                range(len(update_options)),
                format_func=lambda i: update_options[i],
                key="existing_update_index",
            )

            selected_row = updates_df.iloc[selected_index]
            selected_update = selected_row.to_dict()

            render_company_update(selected_update)

            extra_prompt = st.text_area(
                "Optional extra instructions",
                value=st.session_state.get("existing_prompt", ""),
                placeholder="Example: Make it more engaging and concise.",
                height=100,
                key="existing_prompt_widget",
            )

            if st.button("🤖 Generate Draft from Update", use_container_width=True):
                try:
                    with st.spinner("Generating draft..."):
                        update, draft = create_draft(
                            int(selected_update["id"]),
                            platform_to_key(st.session_state["selected_platform"]),
                            st.session_state["selected_tone"].lower(),
                            extra_prompt.strip(),
                        )

                    st.session_state["current_update"] = update
                    st.session_state["current_draft"] = draft
                    st.session_state["research_report"] = ""
                    st.session_state["research_sources"] = []
                    st.success("Draft generated successfully.")
                except Exception as exc:
                    st.error(f"Draft generation failed: {exc}")

    else:
        st.subheader("Manual Company Research")

        company_name = st.text_input(
            "Company name",
            value=st.session_state.get("company_input", ""),
            placeholder="Example: Zoho, TCS, OpenAI, Freshworks",
            key="company_input_widget",
        )

        company_url = st.text_input(
            "Official website (optional)",
            value=st.session_state.get("company_url", ""),
            placeholder="Example: https://company.com",
            key="company_url_widget",
        )

        title_input = st.text_input(
            "Post title / topic",
            value=st.session_state.get("title_input", ""),
            placeholder="Example: New product launch",
            key="title_input_widget",
        )

        user_prompt = st.text_area(
            "What should the post communicate?",
            value=st.session_state.get("user_prompt", ""),
            placeholder="Describe the goal, audience, key points, and call to action.",
            height=160,
            key="user_prompt_widget",
        )

        media_notes = st.text_area(
            "Describe the media or visual context",
            value=st.session_state.get("media_notes", ""),
            placeholder="Example: Team celebration photo, office milestone video, product screenshot.",
            height=100,
            key="media_notes_widget",
        )

        if st.button("🔍 Research & Generate", use_container_width=True):
            company_name = company_name.strip()
            company_url = company_url.strip()
            title_input = title_input.strip()
            user_prompt = user_prompt.strip()
            media_notes = media_notes.strip()

            if not company_name:
                st.error("Please enter a company name.")
            elif not user_prompt:
                st.error("Please describe what the post should communicate.")
            else:
                try:
                    with st.spinner("Researching company and generating draft..."):
                        media_context = media_notes
                        if uploaded_media is not None:
                            media_context = (
                                f"Uploaded {media_type.lower()}: {uploaded_media.name}. "
                                f"{media_context}"
                            ).strip()

                        if HAS_RESEARCH_AGENT:
                            research = research_company(
                                company=company_name,
                                user_prompt=user_prompt,
                                platform=st.session_state["selected_platform"],
                                company_url=company_url or None,
                            )
                            research_report = research.get("report", "")
                            research_sources = research.get("sources", [])
                            draft = generate_platform_post(
                                company=company_name,
                                platform=st.session_state["selected_platform"],
                                tone=st.session_state["selected_tone"],
                                user_prompt=user_prompt,
                                research_report=research_report,
                                media_context=media_context,
                            )
                        else:
                            research_report = (
                                "OpenAI research module is not available in this environment. "
                                "A fallback draft has been created locally."
                            )
                            research_sources = []
                            draft = fallback_manual_draft(
                                company=company_name,
                                platform_label=st.session_state["selected_platform"],
                                tone=st.session_state["selected_tone"],
                                user_prompt=user_prompt,
                                research_report=research_report,
                                media_context=media_context,
                            )

                    st.session_state["current_update"] = {
                        "id": None,
                        "company": company_name,
                        "title": title_input or user_prompt[:60],
                        "type": "manual",
                        "body": user_prompt,
                        "company_url": company_url or None,
                    }
                    st.session_state["current_draft"] = draft
                    st.session_state["research_report"] = research_report
                    st.session_state["research_sources"] = research_sources
                    st.session_state["company_input"] = company_name
                    st.session_state["company_url"] = company_url
                    st.session_state["title_input"] = title_input
                    st.session_state["user_prompt"] = user_prompt
                    st.session_state["media_notes"] = media_notes
                    st.success("Research completed and draft generated.")
                except Exception as exc:
                    fallback_report = f"Research failed: {exc}"
                    st.session_state["research_report"] = fallback_report
                    st.session_state["research_sources"] = []
                    st.session_state["current_update"] = {
                        "id": None,
                        "company": company_name,
                        "title": title_input or user_prompt[:60],
                        "type": "manual",
                        "body": user_prompt,
                        "company_url": company_url or None,
                    }
                    st.session_state["current_draft"] = fallback_manual_draft(
                        company=company_name,
                        platform_label=st.session_state["selected_platform"],
                        tone=st.session_state["selected_tone"],
                        user_prompt=user_prompt,
                        research_report=fallback_report,
                        media_context=media_notes,
                    )
                    st.error(f"Research or generation failed: {exc}")

# Research Tab

with research_tab:
    st.subheader("Research Report")

    report = st.session_state.get("research_report", "")

    if not report:
        st.info("Generate a draft first to see the research report.")
    else:
        st.write(report)
        render_sources(st.session_state.get("research_sources", []))

# Preview Tab

with preview_tab:
    st.subheader("Draft Preview")

    current_draft = st.session_state.get("current_draft")

    if not current_draft:
        st.info("Generate a draft first.")
    else:
        edited_draft = st.text_area(
            "Review and edit your draft",
            value=normalize_draft_text(current_draft),
            height=360,
            key="draft_editor",
        )

        status = st.selectbox(
            "Status",
            ["draft", "approved", "needs_revision"],
            index=0,
            key="draft_status",
        )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("💾 Save to History", use_container_width=True):
                current_update = st.session_state.get("current_update") or {}
                try:
                    post_id = save_post(
                        **build_save_kwargs(
                            current_update=current_update,
                            edited_draft=edited_draft,
                            status=status,
                            platform_label=st.session_state["selected_platform"],
                            tone=st.session_state["selected_tone"],
                            research_report=st.session_state.get("research_report", ""),
                            research_sources=st.session_state.get("research_sources", []),
                            media_type=media_type,
                            media_name=uploaded_media.name if uploaded_media else None,
                            media_notes=st.session_state.get("media_notes", ""),
                            company_mode=st.session_state["company_mode"],
                            user_prompt=st.session_state.get("user_prompt", ""),
                            company_url=st.session_state.get("company_url", ""),
                        )
                    )
                    st.session_state["saved_post_id"] = post_id
                    st.session_state["current_draft"] = edited_draft
                    st.success(f"Draft saved successfully. Post ID: {post_id}")
                except Exception as exc:
                    st.error(f"Save failed: {exc}")

        with col_b:
            if st.button("🔄 Update Saved Draft", use_container_width=True):
                saved_post_id = st.session_state.get("saved_post_id")
                if saved_post_id is None:
                    st.error("Save the draft first before updating it.")
                else:
                    try:
                        update_draft(int(saved_post_id), edited_draft)
                        st.session_state["current_draft"] = edited_draft
                        st.success("Saved draft updated successfully.")
                    except Exception as exc:
                        st.error(f"Update failed: {exc}")

        if st.session_state.get("saved_post_id") is not None:
            st.caption(f"Saved post ID: {st.session_state['saved_post_id']}")

# History Tab

with history_tab:
    st.subheader("Saved Posts")

    rows = load_posts()

    if rows.empty:
        st.info("No posts have been saved yet.")
    else:
        display_rows = rows.copy()

        if "platform" in display_rows.columns:
            display_rows["platform"] = display_rows["platform"].apply(platform_to_label)

        if "status" in display_rows.columns:
            display_rows["status"] = display_rows["status"].apply(pretty_status)

        display_columns = [
            col for col in [
                "id",
                "timestamp",
                "company",
                "title",
                "platform",
                "tone",
                "status",
                "scheduled_time",
                "recommended_time",
                "published_url",
            ] if col in display_rows.columns
        ]

        st.dataframe(
            display_rows[display_columns],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### View Post Details")

        post_ids = rows["id"].astype(int).tolist()
        selected_post_id = st.selectbox(
            "Select post ID",
            options=post_ids,
            key="history_post_selector",
        )

        selected_row = rows[rows["id"] == selected_post_id]
        if not selected_row.empty:
            selected_post = selected_row.iloc[0].to_dict()

            with st.expander(f"Post #{selected_post_id}", expanded=True):
                st.write(f"**Company:** {selected_post.get('company', '')}")
                st.write(f"**Title:** {selected_post.get('title', '')}")
                st.write(f"**Platform:** {platform_to_label(selected_post.get('platform', ''))}")
                st.write(f"**Status:** {pretty_status(selected_post.get('status', ''))}")
                st.write(f"**Publish Mode:** {selected_post.get('publish_mode', '')}")

                if selected_post.get("scheduled_time"):
                    st.write(f"**Scheduled Time:** {selected_post.get('scheduled_time')}")

                if selected_post.get("recommended_time"):
                    st.write(f"**Recommended Time:** {selected_post.get('recommended_time')}")

                if selected_post.get("draft"):
                    st.markdown("**Saved Draft**")
                    st.text_area(
                        "Draft",
                        value=str(selected_post.get("draft", "")),
                        height=240,
                        disabled=True,
                        key=f"history_draft_{selected_post_id}",
                    )

                if selected_post.get("research_summary"):
                    st.markdown("**Research Summary**")
                    st.write(selected_post.get("research_summary"))

                if selected_post.get("published_url"):
                    st.link_button(
                        "Open Published Post",
                        selected_post.get("published_url"),
                    )
# Publish Tab
with publish_tab:
    st.subheader("Publish & Schedule")

    current_update = st.session_state.get("current_update")
    current_draft = st.session_state.get("current_draft")
    saved_post_id = st.session_state.get("saved_post_id")

    if not current_update or not current_draft:
        st.info("Generate and save a draft first.")
    else:
        # selected_platform is stored as a KEY, so we derive the label from it
        selected_platform_key = st.session_state.get("selected_platform", "linkedin")
        selected_platform_label = platform_to_label(selected_platform_key)

        recommendation = get_recommendation(selected_platform_label)

        publish_mode = st.radio(
            "Publishing Mode",
            ["Publish Now", "Schedule Post"],
            horizontal=True,
            key="publish_mode_radio",
        )

        st.markdown("---")

        if publish_mode == "Publish Now":
            st.info(f"This will publish to {selected_platform_label} immediately.")

            if st.button(f"🚀 Publish to {selected_platform_label}", use_container_width=True):
                try:
                    # Build post_data including media info if available
                    post_data = dict(current_update)  # copy so we can add extra fields

                    # Only attach image bytes for image media type
                    if uploaded_media is not None and media_type == "Image":
                        post_data["image_bytes"] = uploaded_media.read()
                        post_data["image_filename"] = uploaded_media.name
                        post_data["media_type"] = media_type

                    result = publish_post(
                        platform=selected_platform_key,
                        content=normalize_draft_text(current_draft),
                        post_data=post_data,
                        company_data=current_update,
                    )

                    message = result.get("message", "Published successfully.")
                    st.success(message)

                    if result.get("response") is not None:
                        st.json(result["response"])

                    published_url = result.get("published_url") or result.get("url")

                    if saved_post_id is not None:
                        update_post_status(
                            int(saved_post_id),
                            status="published",
                            published_url=published_url,
                            publish_mode="published",
                        )

                except Exception as exc:
                    if saved_post_id is not None:
                        try:
                            update_post_status(
                                int(saved_post_id),
                                status="failed",
                                error_message=str(exc),
                            )
                        except Exception:
                            pass
                    st.error(f"Publish failed: {exc}")

            else:
              st.info("Choose a future date and time for automatic publishing.")
              st.caption(
                f"Recommended: {recommendation['label']} — {recommendation['reason']}"
            )

              col1, col2 = st.columns(2)
              with col1:
                 schedule_date = st.date_input("Schedule Date", value=datetime.now().date())
              with col2:
                 schedule_time = st.time_input("Schedule Time", value=recommendation["time"])

              scheduled_datetime = datetime.combine(schedule_date, schedule_time)

              st.success(
                 f"Scheduled for: {scheduled_datetime.strftime('%d %b %Y %I:%M %p')}"
            )

              if st.button("📅 Schedule Post", use_container_width=True):
                 if saved_post_id is None:
                     st.error("Please save the draft first before scheduling.")
                 else:
                    try:
                        schedule_post(
                            int(saved_post_id),
                            scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                            recommended_time=recommendation["label"],
                        )
                        st.success("Post scheduled successfully.")
                    except Exception as exc:
                        st.error(f"Scheduling failed: {exc}")

st.markdown("---")
st.caption("Built with Streamlit, SQLite, and AI-assisted workflows.")
