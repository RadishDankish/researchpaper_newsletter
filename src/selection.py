import json
import os
from datetime import datetime, timezone

from .config_loader import HISTORY_PATH


class History:
    def __init__(self, path=None):
        self.path = path or HISTORY_PATH
        self.data = {"sent": []}
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

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
