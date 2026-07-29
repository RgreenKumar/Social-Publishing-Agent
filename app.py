import os
from datetime import datetime, timedelta, time
import streamlit as st
from src.storage import init_db, save_post_history, load_post_history

try:
    from config import PUBLISH_MODE
except ImportError:
    PUBLISH_MODE = "mock"

try:
    from src.llm_agent import generate_social_content
except Exception:
    generate_social_content = None


st.set_page_config(page_title="Social Content Agent", page_icon="🧠", layout="wide")
init_db()


def get_recommended_time(platform: str) -> tuple[str, datetime]:
    now = datetime.now()
    weekday = now.weekday()

    def next_weekday(target: int) -> datetime:
        days_ahead = (target - weekday) % 7
        if days_ahead == 0 and now.time() > time(10, 0):
            days_ahead = 7
        return now + timedelta(days=days_ahead)

    platform = platform.lower()

    if platform == "linkedin":
        dt = next_weekday(2).replace(hour=9, minute=0, second=0, microsecond=0)
    elif platform == "instagram":
        dt = next_weekday(2).replace(hour=18, minute=0, second=0, microsecond=0)
    elif platform == "facebook":
        dt = next_weekday(1).replace(hour=11, minute=0, second=0, microsecond=0)
    else:
        dt = next_weekday(1).replace(hour=11, minute=0, second=0, microsecond=0)

    return dt.strftime("%d %b %Y, %I:%M %p"), dt


def build_company_payload(
    company_name,
    industry,
    company_about,
    brand_voice,
):
    return {
        "company": company_name.strip(),
        "industry": industry.strip(),
        "about": company_about.strip(),
        "brand_voice": brand_voice.strip(),
    }


def build_post_payload(
    post_type,
    post_topic,
    post_details,
    key_points,
    audience,
    media_type,
    uploaded_file,
    media_note,
):
    file_name = uploaded_file.name if uploaded_file is not None else ""
    return {
        "post_type": post_type.strip(),
        "title": post_topic.strip(),
        "body": post_details.strip(),
        "key_points": key_points.strip(),
        "audience": audience.strip(),
        "media_type": media_type.strip(),
        "media_file_name": file_name,
        "media_note": media_note.strip(),
    }


def generate_fallback(company_data, post_data, platform, tone, use_web_context):
    company = company_data["company"]
    industry = company_data["industry"] or "business"
    about = company_data["about"] or f"{company} operates in {industry}."
    brand_voice = company_data["brand_voice"] or tone
    post_type = post_data["post_type"]
    title = post_data["title"]
    body = post_data["body"]
    key_points = post_data["key_points"]
    audience = post_data["audience"]
    media_type = post_data["media_type"]
    media_file_name = post_data["media_file_name"]
    media_note = post_data["media_note"]

    hook = f"{company}: {title}"

    context_lines = [about]
    if key_points:
        context_lines.append(f"Key points: {key_points}")
    if audience:
        context_lines.append(f"Audience: {audience}")
    if media_type and media_type != "None":
        media_text = f"Attached media: {media_type}"
        if media_file_name:
            media_text += f" ({media_file_name})"
        if media_note:
            media_text += f" - {media_note}"
        context_lines.append(media_text)
    if use_web_context:
        context_lines.append("Use web context if available.")

    tone_prefix_map = {
        "Professional": "We’re pleased to share",
        "Friendly": "Excited to share",
        "Formal": "We would like to announce",
    }
    cta_map = {
        "Professional": "What are your thoughts? Share them in the comments.",
        "Friendly": "Would love to hear what you think.",
        "Formal": "Please share your feedback.",
    }

    tone_prefix = tone_prefix_map.get(tone, "We’re pleased to share")
    cta = cta_map.get(tone, "Share your thoughts.")
    context_block = "\n".join(context_lines)

    main_post = (
        f"{tone_prefix} a {post_type.lower()} from {company}.\n\n"
        f"{body}\n\n"
        f"{context_block}\n\n"
        f"This update reflects our focus on {industry.lower()} and a {brand_voice.lower()} brand voice."
    )

    caption = f"{company} | {title}"
    hashtags = "#BusinessUpdate #BrandStory #Innovation #Growth"

    if platform.lower() == "instagram":
        caption = f"{title}"
        hashtags = "#BrandUpdate #BusinessStory #Innovation #Launch"
    elif platform.lower() == "twitter":
        main_post = f"{company}: {title}\n\n{body[:180]}..."
        caption = f"{company} update"
        hashtags = "#Update #Business #News"

    return {
        "hook": hook,
        "main_post": main_post,
        "caption": caption,
        "cta": cta,
        "hashtags": hashtags,
    }


def generate_content(company_data, post_data, platform, tone, use_web_context):
    if generate_social_content is not None:
        try:
            return generate_social_content(
                company_data=company_data,
                post_data=post_data,
                platform=platform,
                tone=tone,
                use_web_context=use_web_context,
            )
        except Exception:
            pass

    return generate_fallback(company_data, post_data, platform, tone, use_web_context)


if "content_package" not in st.session_state:
    st.session_state.content_package = None
if "company_data" not in st.session_state:
    st.session_state.company_data = None
if "post_data" not in st.session_state:
    st.session_state.post_data = None
if "platform" not in st.session_state:
    st.session_state.platform = "LinkedIn"
if "tone" not in st.session_state:
    st.session_state.tone = "Professional"
if "use_web_context" not in st.session_state:
    st.session_state.use_web_context = True
if "recommended_time_text" not in st.session_state:
    st.session_state.recommended_time_text = None
if "recommended_datetime" not in st.session_state:
    st.session_state.recommended_datetime = None


with st.sidebar:
    st.title("Social Content Agent")
    st.caption("Minimal AI posting workflow")
    use_web_context = st.toggle("Use web context", value=st.session_state.use_web_context)
    platform = st.selectbox("Platform", ["LinkedIn", "Twitter", "Facebook", "Instagram"])
    tone = st.selectbox("Tone", ["Professional", "Friendly", "Formal"])
    st.session_state.use_web_context = use_web_context
    st.session_state.platform = platform
    st.session_state.tone = tone
    st.divider()
    st.caption(f"Mode: {PUBLISH_MODE}")

st.title("Social Content Agent")
st.caption("Generate, review, and save.")

tab1, tab2, tab3 = st.tabs(["Generate", "Review", "History"])

with tab1:
    with st.form("generate_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Company")
            company_name = st.text_input("Company name", placeholder="Enter company name")
            industry = st.text_input("Industry", placeholder="e.g. SaaS, Retail, AI")
            company_about = st.text_area("About", height=100, placeholder="Short company description")
            brand_voice = st.text_input("Brand voice", placeholder="e.g. bold, trusted, modern")

        with col2:
            st.subheader("Post")
            post_type = st.selectbox(
                "Post type",
                [
                    "Product Launch",
                    "Hiring",
                    "Event",
                    "Milestone",
                    "Thought Leadership",
                    "Offer / Promotion",
                    "General Update",
                    "Custom",
                ],
            )
            post_topic = st.text_input("Post title", placeholder="Short title")
            post_details = st.text_area("Post details", height=100, placeholder="What is the update?")
            key_points = st.text_area("Key points", height=80, placeholder="Important points to include")
            audience = st.text_input("Audience", placeholder="e.g. founders, customers, students")

            st.subheader("Media")
            m1, m2 = st.columns([1, 2])

        with m1:
            media_type = st.selectbox("Media type", ["None", "Image", "Video", "Document"])
            uploaded_file = st.file_uploader(
                "Upload file",
                type=["png", "jpg", "jpeg", "mp4", "mov", "pdf", "docx", "pptx"],
                accept_multiple_files=False,
            )
            show_media_preview(uploaded_file, media_type)

        with m2:
            media_note = st.text_area(
                "Media note",
                height=80,
                placeholder="What does the uploaded file show?",
            )

        submitted = st.form_submit_button("Generate", type="primary")

    if submitted:
        if not company_name.strip():
            st.error("Enter company name.")
        elif not post_topic.strip():
            st.error("Enter post title.")
        elif not post_details.strip():
            st.error("Enter post details.")
        else:
            company_data = build_company_payload(
                company_name=company_name,
                industry=industry,
                company_about=company_about,
                brand_voice=brand_voice,
            )
            post_data = build_post_payload(
                post_type=post_type,
                post_topic=post_topic,
                post_details=post_details,
                key_points=key_points,
                audience=audience,
                media_type=media_type,
                uploaded_file=uploaded_file,
                media_note=media_note,
            )

            with st.spinner("Generating...", show_time=True):
                content_package = generate_content(
                    company_data=company_data,
                    post_data=post_data,
                    platform=platform,
                    tone=tone,
                    use_web_context=use_web_context,
                )

            st.session_state.company_data = company_data
            st.session_state.post_data = post_data
            st.session_state.content_package = content_package

            rec_text, rec_dt = get_recommended_time(platform)
            st.session_state.recommended_time_text = rec_text
            st.session_state.recommended_datetime = rec_dt

            st.success("Ready in Review.")

with tab2:
    if not st.session_state.content_package:
        st.info("No draft yet.")
    else:
        package = st.session_state.content_package

        left, right = st.columns([3, 1])

        with right:
            st.metric("Status", "Draft")
            st.metric("Platform", st.session_state.platform)
            if st.session_state.recommended_time_text:
                st.metric("Best time", st.session_state.recommended_time_text)

        with left:
            hook_value = st.text_area("Hook", package["hook"], height=70)
            main_post_value = st.text_area("Main post", package["main_post"], height=220)
            caption_value = st.text_area("Caption", package["caption"], height=70)
            cta_value = st.text_area("CTA", package["cta"], height=70)
            hashtags_value = st.text_area("Hashtags", package["hashtags"], height=70)

        default_dt = st.session_state.recommended_datetime or datetime.now() + timedelta(hours=1)

        s1, s2 = st.columns(2)
        with s1:
            schedule_date = st.date_input(
                "Date",
                value=default_dt.date(),
                min_value=datetime.now().date(),
            )
        with s2:
            schedule_time = st.time_input(
                "Time",
                value=default_dt.time().replace(second=0, microsecond=0),
                step=timedelta(minutes=15),
            )

        scheduled_dt = datetime.combine(schedule_date, schedule_time)

        content_is_valid = all([
            hook_value.strip(),
            main_post_value.strip(),
            caption_value.strip(),
            cta_value.strip(),
            hashtags_value.strip(),
        ])

        formatted_draft = f"""HOOK:
{hook_value}

MAIN POST:
{main_post_value}

CAPTION:
{caption_value}

CTA:
{cta_value}

HASHTAGS:
{hashtags_value}
"""

        a1, a2 = st.columns(2)

        with a1:
            approve = st.button("Approve", type="primary", use_container_width=True)
        with a2:
            reject = st.button("Reject", use_container_width=True)

        if approve:
            if not content_is_valid:
                st.error("Complete all fields.")
            elif scheduled_dt <= datetime.now():
                st.error("Select a future time.")
            else:
                try:
                    company_name = st.session_state.company_data["company"]
                    post_title = st.session_state.post_data["title"]

                    save_post_history(
                        update_id=0,
                        company=company_name,
                        title=post_title,
                        platform=st.session_state.platform,
                        generated_post=formatted_draft,
                        status="Approved",
                        scheduled_time=scheduled_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        recommended_time=st.session_state.recommended_time_text,
                        publish_mode=PUBLISH_MODE,
                    )
                    st.success("Saved.")
                except Exception as e:
                    st.error(f"Save failed: {e}")

        if reject:
            if not content_is_valid:
                st.error("Complete all fields.")
            else:
                try:
                    company_name = st.session_state.company_data["company"]
                    post_title = st.session_state.post_data["title"]

                    save_post_history(
                        update_id=0,
                        company=company_name,
                        title=post_title,
                        platform=st.session_state.platform,
                        generated_post=formatted_draft,
                        status="Rejected",
                        scheduled_time=scheduled_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        recommended_time=st.session_state.recommended_time_text,
                        publish_mode=PUBLISH_MODE,
                    )
                    st.warning("Rejected and saved.")
                except Exception as e:
                    st.error(f"Save failed: {e}")

def show_media_preview(uploaded_file, media_type):
    if uploaded_file is None or media_type == "None":
        return

    file_name = uploaded_file.name.lower()

    if media_type == "Image" or file_name.endswith((".png", ".jpg", ".jpeg")):
        st.image(uploaded_file, caption="Preview", width=180)

    elif media_type == "Video" or file_name.endswith((".mp4", ".mov", ".mpeg", ".mpg", ".m4v")):
        st.video(uploaded_file)

    else:
        st.caption(f"Attached: {uploaded_file.name}")
        
with tab3:
    history_df = load_post_history()

    if history_df.empty:
        st.info("No history.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", len(history_df))
        c2.metric("Approved", int((history_df["status"] == "Approved").sum()))
        c3.metric("Rejected", int((history_df["status"] == "Rejected").sum()))
        c4.metric("Mode", PUBLISH_MODE)

        status_filter = st.selectbox("Filter", ["All", "Approved", "Rejected"], index=0)

        filtered_history = history_df.copy()
        if status_filter != "All":
            filtered_history = filtered_history[filtered_history["status"] == status_filter]

        st.dataframe(filtered_history, use_container_width=True)

        csv = filtered_history.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv,
            file_name="post_history.csv",
            mime="text/csv",
            use_container_width=True,
        )