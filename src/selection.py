import json
import os
from datetime import datetime, timedelta, timezone

from .config_loader import HISTORY_MAX_AGE_DAYS, HISTORY_PATH


class History:
    def __init__(self, path=None, max_age_days=HISTORY_MAX_AGE_DAYS):
        self.path = path or HISTORY_PATH
        self.max_age_days = max_age_days
        self.data = {"sent": []}
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        self.prune()

    def prune(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)
        kept = []
        for entry in self.data.get("sent", []):
            try:
                sent_at = datetime.fromisoformat(entry["sent_at"])
            except (KeyError, TypeError, ValueError):
                continue
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            if sent_at >= cutoff:
                kept.append(entry)
        removed = len(self.data.get("sent", [])) - len(kept)
        if removed:
            print(f"History pruned: dropped {removed} entries older than {self.max_age_days} days")
        self.data["sent"] = kept

    def sent_ids(self, email=None):
        return {
            entry["paper_id"]
            for entry in self.data["sent"]
            if email is None or entry["email"] == email
        }

    def record(self, email, paper, domain_name):
        self.data["sent"].append(
            {
                "email": email,
                "paper_id": paper.id,
                "title": paper.title,
                "domain": domain_name,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)


def select_paper(ranked, already_sent):
    for paper, score, domain_name in ranked:
        if paper.id not in already_sent:
            return paper, domain_name
    return None, None
