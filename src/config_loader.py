import os
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(PROJECT_ROOT, "data", "history.json")
MAX_PAPER_CHARS = 60000
MAX_ABSTRACT_CHARS = 2000


@dataclass
class Domain:
    name: str
    query: str
    categories: list = field(default_factory=list)
    keywords: list = field(default_factory=list)


@dataclass
class User:
    name: str
    email: str
    domains: list = field(default_factory=list)


def _parse_domain(raw):
    return Domain(
        name=raw.get("name", "General"),
        query=raw.get("query", raw.get("name", "")),
        categories=list(raw.get("categories", [])),
        keywords=[k.lower() for k in raw.get("keywords", [])],
    )


def load_users(path=None):
    path = path or os.path.join(PROJECT_ROOT, "config", "users.yaml")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    users = []
    for raw in cfg.get("users", []):
        users.append(
            User(
                name=raw.get("name", raw["email"]),
                email=raw["email"],
                domains=[_parse_domain(d) for d in raw.get("domains", [])],
            )
        )
    return users


def env(key, default=None, required=False):
    value = os.environ.get(key, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value
