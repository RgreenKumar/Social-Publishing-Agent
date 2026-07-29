# Social Publishing Agent MVP

## Overview
Social Publishing Agent MVP is a prototype application that converts company-style updates into social media post drafts. It demonstrates an end-to-end AI-assisted publishing workflow using public sample data, human approval, and status tracking.

This project was built as a prototype, not as a production system. The current version focuses on showing the core workflow clearly and can later be extended with real company data and live social platform integrations.

## Features
- Select a company-style update from sample CSV data
- Generate a social media draft for platforms like LinkedIn, Twitter, and Facebook
- Choose platform and tone
- Review the generated draft before publishing
- Approve or reject the draft
- Store publishing history in SQLite
- Export post history as CSV
- Use fallback mock generation if live API quota is unavailable

## Workflow
1. Select a sample company update
2. Choose target platform and tone
3. Generate a draft post
4. Review the generated content
5. Approve or reject the draft
6. Save the final status in the history log

## Tech Stack
- Python
- Streamlit
- Pandas
- SQLite
- python-dotenv
- OpenAI API (with mock fallback)
- Requests

## Project Structure
```text
social-publishing-agent/
├── app.py
├── config.py
├── .env
├── README.md
├── requirements.txt
├── data/
│   ├── company_updates.csv
│   └── post_history.db
├── prompts/
│   ├── linkedin_prompt.md
│   ├── twitter_prompt.md
│   └── instagram_prompt.md
├── src/
│   ├── data_loader.py
│   ├── llm_agent.py
│   ├── workflow.py
│   ├── storage.py
│   ├── approval.py
│   ├── publisher.py
│   └── platform_adapters/
│       ├── linkedin_adapter.py
│       ├── twitter_adapter.py
│       ├── instagram_adapter.py
│       └── facebook_adapter.py
```

## How to Run
1. Clone the repository
2. Move into the project folder
3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory

```env
OPENAI_API_KEY=your_openai_api_key_here
LINKEDIN_ACCESS_TOKEN=your_linkedin_token_here
LINKEDIN_PERSON_URN=your_linkedin_person_urn_here
META_ACCESS_TOKEN=your_meta_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_business_id_here
PUBLISH_MODE=mock
```

5. Run the Streamlit application

```bash
streamlit run app.py
```

## Current Status
This version is a working MVP that demonstrates:
- input handling
- AI/mock draft generation
- human review
- approval/rejection flow
- status tracking
- CSV export

The app currently uses mock publishing mode for stable demonstration. Real API posting can be added later.

## Future Improvements
- Real LinkedIn posting integration
- Real Instagram professional account integration
- Scheduling support
- Multi-platform publishing in one workflow
- Reviewer roles and authentication
- Analytics dashboard
- Better prompt templates
- Rich text / hashtag controls

## Notes
- Public sample company-style updates are used in place of real company data
- The project is intentionally scoped as a prototype/MVP
- Mock mode is recommended for demos until real API integrations are fully tested

## Author
Built as a prototype Social Publishing Agent project for demonstrating AI content generation, approval workflow, and publishing status tracking.