"""Rewrites the open-source section of README.md from GitHub search.

Counts pull requests by AUTHOR to public repositories owned by someone else
(private work repos never show up, even when run with a personal token) and
lists one row per project, so the table grows with projects, not with PRs.
Closed-without-merge PRs are left out. Runs in GitHub Actions with the gh CLI;
locally it works the same with `gh auth login`.
"""
import json
import re
import subprocess
from collections import defaultdict

AUTHOR = "beiryu"
SINCE = "2024-01-01"  # older PRs were team projects at university
MAX_ROWS = 10


def gh(*args: str):
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


prs = [
    p for p in gh("search", "prs", "--author", AUTHOR, "--created", f">={SINCE}", "--visibility", "public",
                  "--limit", "1000", "--json", "repository,state,createdAt")
    if not p["repository"]["nameWithOwner"].lower().startswith(f"{AUTHOR.lower()}/")
    and p["state"] in ("merged", "open")
]

projects = defaultdict(lambda: {"merged": 0, "open": 0, "latest": ""})
for p in prs:
    r = projects[p["repository"]["nameWithOwner"]]
    r[p["state"]] += 1
    r["latest"] = max(r["latest"], p["createdAt"])

# Most merged first, then the most recently active.
ranked = sorted(projects.items(), key=lambda kv: kv[1]["latest"], reverse=True)
ranked.sort(key=lambda kv: kv[1]["merged"], reverse=True)


def stars(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def short(desc: str | None, limit: int = 70) -> str:
    """First sentence of the repo description, cut at a word boundary."""
    text = re.split(r"(?<=[.!?])\s", (desc or "").strip())[0].rstrip(".")
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text.replace("|", "\\|") or "–"


rows = ["| Project | Description | Language | Stars | Pull requests |", "|---|---|---|--:|--:|"]
for repo, r in ranked[:MAX_ROWS]:
    info = gh("api", f"repos/{repo}", "--jq", "{desc: .description, lang: .language, stars: .stargazers_count}")
    link = f"https://github.com/{repo}/pulls?q=is%3Apr+author%3A{AUTHOR}"
    rows.append(f"| [{repo}](https://github.com/{repo}) | {short(info['desc'])} | {info['lang'] or '–'} "
                f"| {stars(info['stars'])} | [{r['merged'] + r['open']}]({link}) |")

merged_total = sum(r["merged"] for r in projects.values())
open_total = sum(r["open"] for r in projects.values())
summary = (f"{merged_total} merged pull requests across {len(projects)} projects"
           f"{f', {open_total} in review' if open_total else ''}.")
more = len(projects) - MAX_ROWS
block = "\n".join([summary, "", *rows] + ([f"\nAnd {more} more projects."] if more > 0 else []))

readme = open("README.md", encoding="utf-8").read()
new = re.sub(r"(<!-- oss:start -->\n).*?(\n<!-- oss:end -->)", lambda m: m.group(1) + block + m.group(2), readme, flags=re.S)
open("README.md", "w", encoding="utf-8").write(new)
print(summary)
