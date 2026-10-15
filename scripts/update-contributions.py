"""Rewrites the contributions table in README.md from GitHub search.

Lists pull requests by AUTHOR to public repositories owned by someone else
(private work repos never show up, even when run with a personal token),
merged ones first. Closed-without-merge PRs are left out. Runs in GitHub Actions
with the gh CLI; locally it works the same with `gh auth login`.
"""
import json
import re
import subprocess

AUTHOR = "beiryu"
SINCE = "2024-01-01"  # older PRs were team projects at university
LIMIT = 15

out = subprocess.run(
    ["gh", "search", "prs", "--author", AUTHOR, "--created", f">={SINCE}", "--visibility", "public",
     "--limit", "200", "--json", "repository,number,title,state,url,createdAt"],
    check=True, capture_output=True, text=True,
).stdout
prs = [
    p for p in json.loads(out)
    if not p["repository"]["nameWithOwner"].lower().startswith(f"{AUTHOR.lower()}/")
    and p["state"] in ("merged", "open")
]
# Newest first, merged before open (sort is stable).
prs.sort(key=lambda p: p["createdAt"], reverse=True)
prs.sort(key=lambda p: p["state"] != "merged")

def cell(text: str) -> str:
    return text.replace("|", "\\|")

rows = ["| Project | Pull request | Status |", "|---|---|---|"]
for p in prs[:LIMIT]:
    repo = p["repository"]["nameWithOwner"]
    status = "✅ Merged" if p["state"] == "merged" else "🔄 In review"
    rows.append(f"| [{repo}](https://github.com/{repo}) | [{cell(p['title'])}]({p['url']}) | {status} |")

readme = open("README.md", encoding="utf-8").read()
table = "\n".join(rows)
new = re.sub(r"(<!-- oss:start -->\n).*?(\n<!-- oss:end -->)", lambda m: m.group(1) + table + m.group(2), readme, flags=re.S)
open("README.md", "w", encoding="utf-8").write(new)
print(f"{len(prs[:LIMIT])} pull requests listed")
