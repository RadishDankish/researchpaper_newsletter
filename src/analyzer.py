import time

import requests

from .config_loader import env

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PROMPT_TEMPLATE = """You are a research paper explainer for a busy technical reader.
Read the following paper abstract and respond in Markdown with EXACTLY these two sections, in this order:

## In Simple Terms
(plain-language explanation of what the paper does and how it works, 3-4 sentences)

## Why It Matters & Future Uses
(why this paper is worth knowing about, what it enables next, and who should care, 3-4 sentences)

Be accurate to the abstract. Do not invent results, numbers, or claims that are not stated. Keep the whole response under 250 words.

PAPER TITLE: {title}

ABSTRACT:
{abstract}
"""


def _call_model(model, prompt):
    api_key = env("OPENROUTER_API_KEY", required=True)
    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a precise research assistant."},
                {"role": "user", "content": prompt},
            ],
            "reasoning": {"enabled": True},
            "temperature": 0.3,
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"].get("content") or ""


def analyze_paper(title, abstract):
    models = [
        m
        for m in (
            env("OPENROUTER_MODEL_1", "nvidia/nemotron-3-ultra-550b-a55b:free"),
            env("OPENROUTER_MODEL_2", "nvidia/nemotron-3-super-120b-a12b:free"),
        )
        if m
    ]
    prompt = PROMPT_TEMPLATE.format(title=title, abstract=abstract)
    last_error = None
    for i, model in enumerate(models):
        try:
            breakdown = _call_model(model, prompt)
            if breakdown and len(breakdown.strip()) > 200:
                return breakdown, model
            last_error = RuntimeError(f"{model} returned suspiciously short output")
        except Exception as exc:
            last_error = exc
            if i < len(models) - 1:
                time.sleep(5)
    raise RuntimeError(f"All OpenRouter models failed: {last_error}")


def fallback_breakdown(paper):
    authors = ", ".join(paper.authors[:6])
    return (
        "## In Simple Terms\nAutomatic AI analysis failed today, so here are the raw details.\n\n"
        f"{paper.abstract}\n\n"
        f"## Why It Matters & Future Uses\nAuthors: {authors}\n"
        f"Read the full paper: {paper.url}"
    )
