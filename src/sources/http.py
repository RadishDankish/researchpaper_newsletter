import re
import time

import requests

from ..config_loader import MAX_ABSTRACT_CHARS

USER_AGENT = "research-digest-agent/1.0"


def clean_text(text):
    return " ".join((text or "").split())


def strip_markup(text):
    return clean_text(re.sub(r"<[^>]+>", " ", text or ""))


RETRYABLE_STATUS = (429, 500, 502, 503, 504)


def request_json(url, params=None, json_body=None, headers=None, timeout=90, retries=3):
    last_error = None
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    for attempt in range(retries):
        try:
            resp = requests.request(
                "POST" if json_body is not None else "GET",
                url,
                params=params,
                json=json_body,
                headers=merged,
                timeout=timeout,
            )
            if resp.status_code in RETRYABLE_STATUS:
                last_error = RuntimeError(f"HTTP {resp.status_code} from {url}")
                if attempt < retries - 1:
                    time.sleep(min(2 ** attempt, 8))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Request to {url} failed after {retries} attempts: {last_error}")