import json
import time

import requests

from .config_loader import env

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PROMPT_TEMPLATE = """You are a research paper explainer for a busy technical reader.
Read the following paper and produce a breakdown in Markdown with EXACTLY these sections, in this order:

## TL;DR
(2-3 sentences)

## The Problem
(what problem the paper solves and why it matters)

## The Method
(how they did it, explained simply; use bullet points where helpful)

## Key Results
(main findings, include concrete numbers/benchmarks if present)

## Limitations
(caveats, weaknesses, open questions)

## Why It Matters
(who should care and what it enables next)

Be accurate to the paper. Do not invent results. Keep the whole breakdown under 600 words.

PAPER TITLE: {title}

PAPER TEXT:
{text}
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
            "temperature": 0.3,
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def analyze_paper(title, text):
    models = [
        m
        for m in (
            env("OPENROUTER_MODEL_1", "meta-llama/llama-3.3-70b-instruct:free"),
            env("OPENROUTER_MODEL_2", "google/gemini-2.0-flash-exp:free"),
        )
        if m
    ]
    prompt = PROMPT_TEMPLATE.format(title=title, text=text)
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
        f"## TL;DR\nAutomatic AI analysis failed today. Here are the raw details.\n\n"
        f"## Abstract\n{paper.abstract}\n\n"
        f"## Authors\n{authors}"
    )


def safe_json_loads(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None
