import streamlit as st
import pandas as pd

from src.data_loader import load_company_updates
from src.workflow import create_draft
from src.publisher import publish_post
from src.storage import (
    init_db,
    save_post,
    load_posts,
    update_draft,
    update_post_status,
)

try:
    from src.research_agent import research_company, generate_platform_post
    HAS_RESEARCH_AGENT = True
except Exception:
    HAS_RESEARCH_AGENT = False


def init_page():
    st.set_page_config(
        page_title="Social Publishing Agent",
        page_icon="📰",
        layout="wide",
    )
    st.title("Social Publishing Agent")
    st.caption("Draft, review, research, and save social posts across platforms.")


def normalize_draft_text(draft):
    if draft is None:
        return ""

    if isinstance(draft, dict):
        return (
            draft.get("main_post")
            or draft.get("body")
            or draft.get("text")
            or draft.get("caption")
            or str(draft)
        )

    return str(draft)


def show_media_preview(uploaded_file, media_type: str):
    if uploaded_file is None:
        return

    media_type = (media_type or "").lower()

    if media_type == "image":
        st.subheader("Media preview")
        st.image(uploaded_file, caption="Uploaded image", use_container_width=True)
    elif media_type == "video":
        st.subheader("Media preview")
        st.video(uploaded_file)
    else:
        st.info("Preview not available for this media type.")


def render_update_details(update: dict):
    if not update:
        st.warning("No update selected.")
        return

    st.subheader("Selected company update")
    st.write(f"**Company:** {update.get('company', '')}")
    st.write(f"**Title:** {update.get('title', '')}")
    st.write(f"**Type:** {update.get('type', '')}")
    st.write("**Body:**")
    st.write(update.get("body", ""))


def render_draft_output(draft):
    if draft is None:
        st.info("No draft generated yet.")
        return

    st.subheader("Generated draft")

    if isinstance(draft, dict):
        main_post = draft.get("main_post") or draft.get("body") or draft.get("text")
        caption = draft.get("caption")
        hook = draft.get("hook")
        hashtags = draft.get("hashtags")

        if hook:
            st.markdown(f"**Hook:** {hook}")
        if main_post:
            st.markdown("**Main post:**")
            st.write(main_post)
        if caption:
            st.markdown("**Caption:**")
            st.write(caption)
        if hashtags:
            st.markdown("**Hashtags:**")
            st.write(hashtags)
    else:
        st.write(draft)


def render_history():
    st.subheader("Post History")

    try:
        rows = load_posts()

        # load_posts() returns a DataFrame
        if rows.empty:
            st.info("No posts have been saved yet.")
            return

        preferred_columns = [
            "id",
            "timestamp",
            "company",
            "title",
            "platform",
            "tone",
            "status",
            "publish_mode",
            "scheduled_time",
            "published_url",
        ]

        display_columns = [col for col in preferred_columns if col in rows.columns]

        st.dataframe(
            rows[display_columns],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### View saved post")

        post_ids = rows["id"].astype(int).tolist()

        selected_post_id = st.selectbox(
            "Select post ID",
            options=post_ids,
            key="history_post_id",
        )

        selected_rows = rows[rows["id"] == selected_post_id]

        if selected_rows.empty:
            return

        selected_post = selected_rows.iloc[0]

        with st.expander(f"Post #{selected_post_id}", expanded=True):
            st.markdown(f"**Company:** {selected_post.get('company', '')}")
            st.markdown(f"**Platform:** {selected_post.get('platform', '')}")
            st.markdown(f"**Status:** {selected_post.get('status', '')}")

            st.text_area(
                "Saved draft",
                value=str(selected_post.get("draft", "")),
                height=250,
                disabled=True,
                key=f"saved_draft_{selected_post_id}",
            )

            research = selected_post.get("research_summary", None)
            if research and not pd.isna(research):
                st.markdown("#### Research report")
                st.write(research)

            published_url = selected_post.get("published_url", None)
            if published_url and not pd.isna(published_url):
                st.link_button("Open published post", published_url)

    except Exception as error:
        st.error(f"Unable to load history: {error}")


def main():
    init_db()
    init_page()

    # session defaults
    st.session_state.setdefault("current_update", None)
    st.session_state.setdefault("current_draft", None)
    st.session_state.setdefault("research_report", None)
    st.session_state.setdefault("research_sources", [])
    st.session_state.setdefault("saved_post_id", None)
    st.session_state.setdefault("company_input", "")
    st.session_state.setdefault("company_url", "")
    st.session_state.setdefault("title_input", "")
    st.session_state.setdefault("user_prompt", "")
    st.session_state.setdefault("media_notes", "")
    st.session_state.setdefault("media_name", None)
    st.session_state.setdefault("media_type", None)

    # Sidebar settings
    st.sidebar.header("Draft settings")

    workflow_mode = st.sidebar.radio(
        "Workflow mode",
        ["Manual company research", "Existing company updates"],
        index=0,
    )

    platform = st.sidebar.selectbox(
        "Platform",
        ["LinkedIn", "Twitter/X", "Facebook", "Instagram"],
    )

    tone = st.sidebar.selectbox(
        "Tone",
        ["Professional", "Friendly", "Neutral", "Confident", "Celebratory"],
    )

    media_type = st.sidebar.selectbox(
        "Media type",
        ["None", "Image", "Video"],
    )

    uploaded_file = None
    if media_type != "None":
        uploaded_file = st.sidebar.file_uploader(
            "Upload media",
            type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "avi"],
        )

    # Tabs
    create_tab, research_tab, preview_tab, history_tab, publish_tab = st.tabs(
        ["✍️ Create Post", "🌐 Research", "📝 Draft Preview", "📚 History", "🚀 Publish"]
    )

    with create_tab:
        if workflow_mode == "Existing company updates":
            updates_df = load_company_updates()

            if updates_df.empty:
                st.error("No company updates found in data/company_updates.csv.")
            else:
                st.subheader("Choose an existing company update")

                update_options = [
                    f"{int(row.id)} – {row.company} | {row.title}"
                    for _, row in updates_df.iterrows()
                ]
                update_ids = [int(row.id) for _, row in updates_df.iterrows()]

                selected_idx = st.selectbox(
                    "Select company update",
                    options=list(range(len(update_options))),
                    format_func=lambda i: update_options[i],
                )
                selected_update_id = update_ids[selected_idx]

                update_row = updates_df[updates_df["id"] == selected_update_id].iloc[0]
                update = update_row.to_dict()

                render_update_details(update)

                if st.button("Generate draft from update", use_container_width=True):
                    with st.spinner("Generating draft..."):
                        generated_update, draft = create_draft(
                            selected_update_id,
                            platform.lower(),
                            tone.lower(),
                        )

                    if generated_update is None or draft is None:
                        st.error("Failed to generate draft. Please check the workflow setup.")
                    else:
                        st.session_state["current_update"] = generated_update
                        st.session_state["current_draft"] = draft
                        st.session_state["research_report"] = None
                        st.session_state["research_sources"] = []
                        st.success("Draft generated successfully.")

        else:
            st.subheader("Manual company research flow")

            st.session_state["company_input"] = st.text_input(
                "Company name",
                value=st.session_state.get("company_input", ""),
                placeholder="Example: Zoho, TCS, OpenAI, Freshworks",
            )

            st.session_state["company_url"] = st.text_input(
                "Official company website — optional",
                value=st.session_state.get("company_url", ""),
                placeholder="Helps when company names are similar",
            )

            st.session_state["title_input"] = st.text_input(
                "Post topic / title",
                value=st.session_state.get("title_input", ""),
                placeholder="Example: Product launch, internship update, milestone, hiring post",
            )

            st.session_state["user_prompt"] = st.text_area(
                "What should the post say?",
                value=st.session_state.get("user_prompt", ""),
                height=160,
                placeholder=(
                    "Explain the message, target audience, call to action, "
                    "and anything that must be included."
                ),
            )

            st.session_state["media_notes"] = st.text_area(
                "Describe the image/video or planned media",
                value=st.session_state.get("media_notes", ""),
                height=120,
                placeholder="Example: Team receiving award on stage, product screenshot, office celebration...",
            )

            if media_type != "None" and uploaded_file is not None:
                show_media_preview(uploaded_file, media_type)

            if not HAS_RESEARCH_AGENT:
                st.warning(
                    "The research-based generator is not available yet. Create src/research_agent.py first."
                )

            if st.button("🌐 Research company and generate draft", use_container_width=True):
                company = st.session_state["company_input"].strip()
                company_url = st.session_state["company_url"].strip()
                title = st.session_state["title_input"].strip()
                user_prompt = st.session_state["user_prompt"].strip()
                media_notes = st.session_state["media_notes"].strip()

                if not company:
                    st.error("Please enter a company name.")
                elif not user_prompt:
                    st.error("Please describe what the post should communicate.")
                elif not HAS_RESEARCH_AGENT:
                    st.error("Add src/research_agent.py before using web research mode.")
                else:
                    try:
                        with st.spinner("Researching company and generating draft..."):
                            research_result = research_company(
                                company=company,
                                user_prompt=user_prompt,
                                platform=platform,
                                company_url=company_url or None,
                            )

                            media_context = media_notes
                            if uploaded_file is not None:
                                media_context = (
                                    f"Uploaded media: {uploaded_file.name} | "
                                    f"MIME type: {uploaded_file.type}\n{media_notes}"
                                ).strip()

                            draft = generate_platform_post(
                                company=company,
                                platform=platform,
                                tone=tone,
                                user_prompt=user_prompt,
                                research_report=research_result["report"],
                                media_context=media_context,
                            )

                        st.session_state["current_update"] = {
                            "id": None,
                            "company": company,
                            "title": title or user_prompt[:60],
                            "type": "manual",
                            "body": user_prompt,
                            "company_url": company_url or None,
                        }
                        st.session_state["current_draft"] = draft
                        st.session_state["research_report"] = research_result["report"]
                        st.session_state["research_sources"] = research_result["sources"]
                        st.session_state["media_name"] = uploaded_file.name if uploaded_file else None
                        st.session_state["media_type"] = uploaded_file.type if uploaded_file else None

                        st.success("Research completed and draft generated.")

                    except Exception as error:
                        st.error(f"Research or generation failed: {error}")

  
    with research_tab:
        st.subheader("Company research")

        report = st.session_state.get("research_report")

        if not report:
            st.info("Generate a draft first to see the research report.")
        else:
            st.write(report)

            sources = st.session_state.get("research_sources", [])
            if sources:
                st.markdown("### Sources")
                for source in sources:
                    title = source.get("title", "Source")
                    url = source.get("url", "")
                    if url:
                        st.markdown(f"- [{title}]({url})")

    with preview_tab:
        st.subheader("Generated draft")

        current_draft = st.session_state.get("current_draft")

        if not current_draft:
            st.info("Generate a draft first.")
        else:
            edited_draft = st.text_area(
                "Review and edit",
                value=normalize_draft_text(current_draft),
                height=350,
                key="edited_draft",
            )

            status = st.selectbox(
                "Status",
                ["draft", "approved", "needs_revision"],
            )

            if st.button("💾 Save draft to history", use_container_width=True):
                current_update = st.session_state.get("current_update")

                if not current_update:
                    st.error("No post metadata found. Generate a draft first.")
                else:
                    try:
                        post_id = save_post(
                            update_id=current_update.get("id"),
                            company=current_update.get("company", ""),
                            title=current_update.get("title", ""),
                            platform=platform,
                            draft=edited_draft,
                            status=status,
                            publish_mode="web_research" if workflow_mode == "Manual company research" else "old_flow",
                            tone=tone,
                            user_prompt=st.session_state.get("user_prompt", ""),
                            company_url=st.session_state.get("company_url", ""),
                            research_summary=st.session_state.get("research_report", None),
                            source_urls=st.session_state.get("research_sources", []),
                            media_name=st.session_state.get("media_name", None),
                            media_type=st.session_state.get("media_type", None),
                            media_notes=st.session_state.get("media_notes", ""),
                        )
                        st.session_state["saved_post_id"] = post_id
                        st.session_state["current_draft"] = edited_draft
                        st.success(f"Draft saved to history. Post ID: {post_id}")
                    except TypeError as e:
                        st.error(f"Save failed due to argument mismatch: {e}")
                    except Exception as e:
                        st.error(f"Save failed: {e}")

            if st.button("🔄 Update saved draft text", use_container_width=True):
                current_update = st.session_state.get("current_update")
                if not current_update:
                    st.error("No post selected.")
                else:
                    try:
                        update_draft(
                            int(st.session_state.get("saved_post_id")),
                            edited_draft,
                        )
                        st.success("Draft updated in history.")
                    except Exception as e:
                        st.error(f"Update failed: {e}")

    with history_tab:
        render_history()

    
    with publish_tab:
        st.subheader("Publish to LinkedIn")

        current_update = st.session_state.get("current_update")
        current_draft = st.session_state.get("current_draft")
        saved_post_id = st.session_state.get("saved_post_id")

        if not current_update or not current_draft:
            st.info("Generate and save a draft first.")
        else:
            st.write("Ready to publish the current draft.")

            if st.button("🚀 Publish to LinkedIn", use_container_width=True):
                try:
                    result = publish_post(
                        platform="linkedin",
                        content=normalize_draft_text(current_draft),
                        company_data=current_update,
                        post_data=current_update,
                    )

                    message = result.get("message", "Published successfully.")
                    st.success(message)

                    if "response" in result:
                        st.json(result["response"])

                    # Update DB if we have a saved row
                    if saved_post_id:
                        try:
                            update_post_status(
                                int(saved_post_id),
                                "published",
                                published_url=result.get("published_url") or result.get("url"),
                            )
                        except Exception:
                            pass

                except Exception as e:
                    if saved_post_id:
                        try:
                            update_post_status(
                                int(saved_post_id),
                                "failed",
                                error_message=str(e),
                            )
                        except Exception:
                            pass
                    st.error(str(e))


if __name__ == "__main__":
    main()