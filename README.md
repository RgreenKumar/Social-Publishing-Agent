# AI Social Publishing Agent

AI Social Publishing Agent is a Streamlit-based application that turns structured company updates and manual research into platform-ready social media posts. It combines CSV data loading, AI-assisted copy generation, media previews, research workflows, scheduling, and SQLite-backed history tracking in a single dashboard.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Using the App](#using-the-app)
  - [Dashboard](#dashboard)
  - [Create Post](#create-post)
  - [Research](#research)
  - [Preview & Save](#preview--save)
  - [History](#history)
  - [Publish & Schedule](#publish--schedule)
- [Data & Storage](#data--storage)
- [Development Notes](#development-notes)
- [Troubleshooting](#troubleshooting)

## Features

- Generate social media drafts for LinkedIn, Twitter/X, Facebook, and Instagram.
- Two content workflows:
  - **Existing Company Update**: use rows from `data/company_updates.csv`.
  - **Manual Company Research**: describe the company and desired post; optionally use a research agent.
- Built-in tone control: Professional, Friendly, Formal, Excited, Marketing, Neutral.
- Optional AI-powered research step for richer context and source links.
- Media handling with image/video upload and preview.
- Draft editing with status labels (Draft, Approved, Needs Revision).
- SQLite-backed history: save, update, and inspect past posts.
- Basic analytics: total posts and counts by status.
- Scheduling and one-click publishing helper for your platform integration.

## Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) for the interactive dashboard.
- **Language**: Python 3.
- **Data**: CSV for company updates.
- **Database**: SQLite (`data/post_history.db`).
- **AI/LLM**: `src/llm_agent.py` and optional `src/research_agent.py` (implementation depends on your environment).

## Project Structure

```text
Social-Publishing-Agent/
├── app.py                 # Streamlit app entrypoint
├── config.py              # Configuration helpers (model names, paths, etc.)
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore rules
├── data/
│   ├── company_updates.csv  # Source company updates (input)
│   └── post_history.db      # SQLite database (auto-created)
└── src/
    ├── data_loader.py       # Load CSV and get update by ID
    ├── llm_agent.py         # Generate social post text
    ├── publisher.py         # Platform publishing helper
    ├── research_agent.py    # Optional research + generation
    ├── storage.py           # SQLite helpers (init, save, load, update, schedule)
    ├── workflow.py          # High-level draft creation
    └── platform_adapters/
        ├── facebook_adapter.py
        ├── instagram_adapter.py
        ├── linkedin_adapter.py
        └── twitter_adapter.py
```

> Note: Database files, environment files, and local `.streamlit` configuration should **not** be committed to Git. See the `.gitignore` section in your repo for details.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/RgreenKumar/Social-Publishing-Agent.git
cd Social-Publishing-Agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

The app expects:

- A CSV file at `data/company_updates.csv` with at least an `id` column and fields like `company`, `title`, `body`, and `type`.
- A SQLite database file at `data/post_history.db` (auto-created).
- Any AI / API keys configured via environment variables, `config.py`, or Streamlit secrets.

Typical configuration files and variables:

- **`.env`** (not committed):

  ```env
  OPENAI_API_KEY=your_api_key_here
  MODEL_NAME=your_model_name
  ```

- **`.streamlit/secrets.toml`** (local only):

  ```toml
  OPENAI_API_KEY = "your_api_key_here"
  MODEL_NAME = "your_model_name"
  ```

Adjust `config.py`, `llm_agent.py`, and `research_agent.py` to match the AI provider, model names, and authentication you use.

## Running the App

From the project root, with your virtual environment active:

```bash
streamlit run app.py
```

This opens the **AI Social Publishing Agent** dashboard in your browser.

## Using the App

The UI is organized into a sidebar and six main tabs: **Dashboard**, **Create Post**, **Research**, **Preview**, **History**, and **Publish**.

### Dashboard

- Shows total posts and counts by status (Draft, Scheduled, Published, Failed).
- Displays a short explanation of how to use the app.
- Recommends posting times for the currently selected platform.
- Lists a small table of recent posts for quick overview.

### Create Post

Use this tab to generate a new draft.

1. **Choose Company Source (sidebar)**
   - **Existing Company Update**: work from `data/company_updates.csv`.
   - **Manual Company Research**: describe the company and desired post.

2. **Select Platform and Tone (sidebar)**
   - Platforms: LinkedIn, Twitter/X, Facebook, Instagram.
   - Tone: Professional, Friendly, Formal, Excited, Marketing, Neutral.

3. **Optionally Add Media (sidebar)**
   - Choose media type: None, Image, or Video.
   - Upload a file to see a preview.

4. **If using Existing Company Update**
   - The app loads rows from `data/company_updates.csv`.
   - Choose a row from the dropdown (ID | Company | Title).
   - Review the update details (company, title, type, body).
   - Optionally add extra instructions (e.g. "Make it concise and engaging.").
   - Click **"🤖 Generate Draft from Update"**.

5. **If using Manual Company Research**
   - Fill in:
     - Company name.
     - Official website (optional).
     - Post title or topic.
     - What the post should communicate (goal, audience, key points, CTA).
     - Media / visual context.
   - Click **"🔍 Research & Generate"**.
   - If the research agent is available, the app retrieves a research summary and draft.
   - If not, it falls back to a locally generated draft based on your inputs.

After generation, the selected update and draft are stored in session state and become visible in the other tabs.

### Research

- Shows the **research report** associated with the current draft.
- Lists any source links returned by the research agent.
- If no report exists, the tab will prompt you to generate a draft first.

### Preview & Save

Use this tab to refine and store your draft.

1. Edit the generated draft text in the text area.
2. Choose a status for the draft: Draft, Approved, Needs Revision.
3. Click **"💾 Save to History"** to insert a new record into the SQLite database.
   - The app stores metadata such as update ID, company, title, platform, tone, research summary, and media details.
4. Optionally click **"🔄 Update Saved Draft"** to overwrite the draft content for the last saved post.

The saved post ID will be shown so you can track which history entry corresponds to your current draft.

### History

- Displays a table of all saved posts.
- Shows key columns such as ID, timestamp, company, title, platform, tone, status, scheduled time, recommended time, and published URL (depending on schema).
- Lets you select a specific post ID to inspect full details:
  - Company, title, platform, status, publish mode.
  - Scheduled time and recommended time.
  - Saved draft content.
  - Research summary (if any).
  - Published URL, when available.

### Publish & Schedule

Use this tab to publish now or schedule a post for later.

1. Ensure a draft is generated and saved (so it has a post ID).
2. Choose **Publish Now** or **Schedule Post**.

**Publish Now**

- The app sends the current draft to the `publisher` module for the selected platform.
- On success, it shows a message and any raw API response.
- If a published URL is returned, the history entry is updated with status `published` and the URL.
- On failure, the history entry can be updated with status `failed` and an error message.

**Schedule Post**

- Choose a future date and time.
- The app shows the formatted scheduled datetime plus a recommended time label.
- Click **"📅 Schedule Post"** to save the schedule metadata to the database.
- It is up to your deployment or background jobs to honor this schedule and call the publisher at the right time.

## Data & Storage

All post history is stored in SQLite via `src/storage.py`.

The `posts` table includes columns such as:

- `id`: auto-increment primary key.
- `timestamp`: when the record was created.
- `update_id`: source company update ID (if any).
- `company`: company name.
- `title`: update or post title.
- `platform`: platform key (e.g. `linkedin`, `twitter`).
- `draft`: saved draft text.
- `status`: draft status.

Additional columns may be present for tone, scheduled time, recommended time, publish mode, research summary, media info, and published URL, depending on your exact implementation.

The `storage` module exposes helpers to:

- Initialize the database and create the `posts` table when the app starts.
- Save a new post.
- Load posts for dashboards and history views.
- Update an existing draft.
- Update post status and published URL.
- Schedule posts and compute statistics.

## Development Notes

- Keep secrets out of version control: use `.env` or Streamlit secrets.
- Do not commit `post_history.db` or local `.streamlit` config to Git.
- Validate the CSV structure before relying on it in production.
- Extend `publisher.py` and the platform adapters to integrate with real APIs.
- Add tests for `data_loader.py`, `workflow.py`, and `storage.py` as the core logic.
- Consider Docker or other deployment methods for production use.

## Troubleshooting

**Import errors**

- Ensure the virtual environment is active.
- Run `pip install -r requirements.txt` again.
- Run `streamlit run app.py` from the project root.

**CSV errors**

- Confirm `data/company_updates.csv` exists.
- Make sure it has an `id` column and valid data.

**Database errors**

- Check that the `data/` directory is writable.
- Delete `post_history.db` if the schema becomes corrupted (it will be recreated).

**Research agent not available**

- The app gracefully falls back to a local draft generator when the research agent cannot be imported.
- Configure your AI credentials and `research_agent.py` to enable full functionality.

**Publishing issues**

- Verify your platform credentials and API permissions.
- Add logging inside `publisher.py` and adapters for debugging.

---

This README is designed to help new users understand, install, and use the AI Social Publishing Agent without needing to read the entire codebase first.
