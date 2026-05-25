from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"

if load_dotenv is not None:
    load_dotenv(ROOT_DIR / ".env")

DB_PATH = Path(os.getenv("BUZZWIRE_DB", DATA_DIR / "buzzwire.db"))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
PAGE_PROFILES_PATH = CONFIG_DIR / "page_profiles.json"
RSS_FEEDS_PATH = CONFIG_DIR / "rss_feeds.json"
MODEL_PROVIDER = os.getenv("BUZZWIRE_MODEL_PROVIDER", "rule_based").strip().lower()
