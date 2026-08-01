import os

PUBLISH_MODE = os.getenv("PUBLISH_MODE", "mock").strip().lower()
if PUBLISH_MODE not in {"mock", "real"}:
    PUBLISH_MODE = "mock"

APP_NAME = os.getenv("APP_NAME", "Social Content Agent")
DEFAULT_PLATFORM = os.getenv("DEFAULT_PLATFORM", "LinkedIn")
DEFAULT_TONE = os.getenv("DEFAULT_TONE", "Professional")
USE_WEB_CONTEXT = os.getenv("USE_WEB_CONTEXT", "true").strip().lower() in {"1", "true", "yes", "on"}

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")