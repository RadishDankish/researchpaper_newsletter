import sys
import traceback
from datetime import datetime, timezone

from .analyzer import analyze_paper, fallback_breakdown
from .config_loader import CITATIONS_ENABLED, ESTABLISHED_EVERY_NTH_SEND, load_users
from .discovery import discover, discover_established, rank_papers, select_established
from .emailer import render_html, send_email
from .selection import History, select_paper
from .sources import fetch_citations

DRY_RUN = "--dry-run" in sys.argv


def enrich_citations(papers, label):
    try:
        enriched = fetch_citations(papers, enabled=CITATIONS_ENABLED)
        print(f"[{label}] citations enriched for {enriched}/{len(papers)} papers")
    except Exception as exc:
        print(f"[{label}] citation lookup failed, ranking without it: {exc}")
    return papers


def should_use_established(history, email):
    if ESTABLISHED_EVERY_NTH_SEND <= 0:
        return False
    sent_count = len([e for e in history.data.get("sent", []) if e.get("email") == email])
    return sent_count > 0 and sent_count % ESTABLISHED_EVERY_NTH_SEND == ESTABLISHED_EVERY_NTH_SEND - 1


def pick_established(user, history):
    papers = discover_established(user.domains)
    if not papers:
        raise RuntimeError("No established papers discovered")
    enrich_citations(papers, user.name)
    paper, domain_name = select_established(papers, user.domains, history.sent_ids(email=user.email))
    if paper is None:
        raise RuntimeError("All high-impact candidates were already sent")
    print(
        f"[{user.name}] established pick: {paper.title} ({domain_name}, "
        f"citations={paper.citations}, influential={paper.influential_citations})"
    )
    return paper, domain_name


def pick_fresh(user, history):
    all_papers = []
    for domain in user.domains:
        try:
            papers = discover(domain)
            print(f"[{user.name}] {domain.name}: found {len(papers)} papers")
            all_papers.extend(papers)
        except Exception as exc:
            print(f"[{user.name}] discovery failed for {domain.name}: {exc}")

    if not all_papers:
        raise RuntimeError("No papers discovered from any domain")

    unique = {p.id: p for p in all_papers}
    enrich_citations(list(unique.values()), user.name)

    ranked = rank_papers(list(unique.values()), user.domains)
    paper, domain_name = select_paper(ranked, history.sent_ids(email=user.email))
    if paper is None:
        raise RuntimeError("All candidate papers were already sent")

    print(
        f"[{user.name}] selected: {paper.title} ({domain_name}, "
        f"score={score_of(ranked, paper)}, source={paper.source}, "
        f"citations={paper.citations}, upvotes={paper.upvotes})"
    )
    return paper, domain_name


def process_user(user, history):
    if should_use_established(history, user.email):
        paper, domain_name = pick_established(user, history)
    else:
        paper, domain_name = pick_fresh(user, history)

    try:
        breakdown, model = analyze_paper(paper.title, paper.abstract)
        print(f"[{user.name}] analyzed with model: {model}")
    except Exception as exc:
        print(f"[{user.name}] AI analysis failed, using fallback: {exc}")
        breakdown = fallback_breakdown(paper)

    html = render_html(paper, breakdown, domain_name)

    if DRY_RUN:
        out_path = f"dry_run_{user.name}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[{user.name}] dry run: wrote preview to {out_path}")
    else:
        subject = f"📄 Today's paper: {paper.title[:80]}"
        send_email(user.email, subject, html)
        print(f"[{user.name}] email sent to {user.email}")

    history.record(user.email, paper, domain_name)


def score_of(ranked, paper):
    for p, score, _ in ranked:
        if p.id == paper.id:
            return score
    return "?"


def main():
    users = load_users()
    if not users:
        print("No users configured in config/users.yaml")
        sys.exit(1)

    history = History()
    failures = 0

    for user in users:
        try:
            process_user(user, history)
        except Exception:
            failures += 1
            print(f"[{user.name}] FAILED:")
            traceback.print_exc()

    if not DRY_RUN and failures == 0:
        history.save()
        print(f"History saved ({len(history.data['sent'])} total sends)")

    print(f"Done at {datetime.now(timezone.utc).isoformat()}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
