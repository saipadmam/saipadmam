#!/usr/bin/env python3
"""Update the GitHub Snapshot section without image-based cards."""

from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request


USERNAME = "saipadmam"
README_PATH = pathlib.Path("README.md")
START = "<!-- GITHUB_SNAPSHOT:START -->"
END = "<!-- GITHUB_SNAPSHOT:END -->"


def github_get(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def paged_github_get(url: str):
    page = 1
    items = []
    while True:
        separator = "&" if "?" in url else "?"
        page_url = f"{url}{separator}per_page=100&page={page}"
        batch = github_get(page_url)
        if not batch:
            return items
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def mermaid_label(label: str) -> str:
    return label.replace('"', "'")


def build_snapshot() -> str:
    repos = paged_github_get(f"https://api.github.com/users/{USERNAME}/repos?sort=updated")

    language_bytes: dict[str, int] = {}
    total_stars = 0
    for repo in repos:
        total_stars += int(repo.get("stargazers_count", 0))
        languages_url = repo.get("languages_url")
        if not languages_url:
            continue
        try:
            for language, byte_count in github_get(languages_url).items():
                language_bytes[language] = language_bytes.get(language, 0) + int(byte_count)
        except urllib.error.HTTPError:
            continue

    top_languages = sorted(language_bytes.items(), key=lambda item: item[1], reverse=True)[:6]
    if not top_languages:
        chart = "_Language data will appear here after GitHub indexes repository languages._"
        top_language_text = "Indexing"
    else:
        chart_lines = ["```mermaid", "pie showData", '    title Public repo language mix']
        chart_lines.extend(f'    "{mermaid_label(language)}" : {byte_count}' for language, byte_count in top_languages)
        chart_lines.append("```")
        chart = "\n".join(chart_lines)
        top_language_text = ", ".join(language for language, _ in top_languages[:4])

    return f"""{START}
<!-- Auto-updated by .github/workflows/update-profile-snapshot.yml. -->

{chart}

**Snapshot**

- Public repositories analyzed: **{len(repos)}**
- Total public stars: **{total_stars}**
- Top languages: **{top_language_text}**
- Refresh cadence: **hourly when data changes**

{END}"""


def main() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    snapshot = build_snapshot()

    if START in readme and END in readme:
        before = readme.split(START, 1)[0]
        after = readme.split(END, 1)[1]
        updated = before + snapshot + after
    else:
        old_section = """<p align="center">
  <img alt="Sai's GitHub profile summary" src="https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=saipadmam&theme=github_dark" />
</p>

<p align="center">
  <img width="49%" alt="Sai's repos by language" src="https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username=saipadmam&theme=github_dark" />
  <img width="49%" alt="Sai's most committed languages" src="https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username=saipadmam&theme=github_dark" />
</p>"""
        updated = readme.replace(old_section, snapshot)

    README_PATH.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
