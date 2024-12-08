import json
import os
from typing import Set, Dict, Any

from dotenv import load_dotenv

from apartment_post_filter import ApartmentFilter, PostFilter

# Load environment variables
load_dotenv("../.env")

# Load configuration from JSON file
with open('../apartments_finder_config.json', encoding='utf-8') as f:
    _apartments_finder_config: Dict[str, Any] = json.load(f)


class Config:
    # OpenAI API Key
    OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]

    # Telegram Bot Configuration
    TELEGRAM_BOT_API_KEY: str = os.environ["TELEGRAM_BOT_API_KEY"]
    TELEGRAM_BOT_APARTMENTS_GROUP_CHAT_ID: str = os.environ[
        "TELEGRAM_BOT_APARTMENTS_GROUP_CHAT_ID"
    ]
    TELEGRAM_BOT_APARTMENTS_LOGS_GROUP_CHAT_ID: str = os.environ.get(
        "TELEGRAM_BOT_APARTMENTS_LOGS_GROUP_CHAT_ID"
    )

    # Facebook Configuration
    FACEBOOK_USERNAME: str = os.environ["FACEBOOK_USERNAME"]
    FACEBOOK_PASSWORD: str = os.environ["FACEBOOK_PASSWORD"]
    FACEBOOK_GROUPS: Set[str] = {
        v.strip() for v in os.environ["FACEBOOK_GROUPS"].split(",") if v
    }

    # Facebook Backup Codes for 2FA
    FACEBOOK_BACKUP_CODES: list[str] = [
        code.strip() for code in os.environ.get("FACEBOOK_BACKUP_CODES", "").split(",") if code
    ]

    # Post Filters Configuration
    MAX_TEXT_LEN: int = 800
    MAX_MINUTES_DIFFERENCE: int = 150

    # Apartment Filters
    APARTMENT_FILTERS = [ApartmentFilter(**f) for f in _apartments_finder_config['apartment_filters']]
    POST_FILTERS = [PostFilter(**f) for f in _apartments_finder_config['post_filters']]

    # Limits for Posts and Enrichment
    MAX_POSTS_TO_ENRICH_IN_RUN = _apartments_finder_config['max_posts_to_enrich_in_run']
    POSTS_PER_GROUP_LIMIT = _apartments_finder_config['posts_per_group_limit']
    TOTAL_POSTS_LIMIT = _apartments_finder_config['total_posts_limit']


# Instantiate Config
config = Config()
