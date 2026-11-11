#!/usr/bin/env python3
"""Generate self-hosted GitHub profile stats cards as SVG files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


USERNAME = "lewiitech-25"
API_BASE = "https://api.github.com"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets"
COLORS = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185", "#64748b"]


def api_get(url: str) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{USERNAME}-profile-stats",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"GitHub API request failed for {url}: {error}") from error


def fetch_repositories() -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        result = api_get(
            f"{API_BASE}/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
        )
        if not isinstance(result, list):
            raise RuntimeError("GitHub API returned an unexpected repository response.")
        if not result:
            return repositories
        repositories.extend(result)
        page += 1


def svg_document(title: str, description: str, content: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="230" viewBox="0 0 500 230" role="img" aria-labelledby="title description">
  <title id="title">{escape(title)}</title>
  <desc id="description">{escape(description)}</desc>
  <rect x="1" y="1" width="498" height="228" rx="14" fill="#1b2832" stroke="#64748b" stroke-width="2"/>
  {content}
</svg>
"""


def generate_stats_card(user: dict, repositories: list[dict]) -> str:
    metrics = [
        ("PUBLIC REPOSITORIES", len(repositories)),
        ("STARS EARNED", sum(repo["stargazers_count"] for repo in repositories)),
        ("FORKS", sum(repo["forks_count"] for repo in repositories)),
        ("FOLLOWERS", user["followers"]),
    ]
    rows = []
    positions = [(36, 92), (268, 92), (36, 158), (268, 158)]
    for (label, value), (x, y) in zip(metrics, positions):
        rows.append(
            f'<text x="{x}" y="{y}" fill="#cbd5e1" font-family="Segoe UI,Arial,sans-serif" font-size="12" font-weight="600">{escape(label)}</text>'
            f'<text x="{x}" y="{y + 31}" fill="#f8fafc" font-family="Segoe UI,Arial,sans-serif" font-size="25" font-weight="700">{value:,}</text>'
        )

    content = (
        '<text x="36" y="49" fill="#f8fafc" font-family="Segoe UI,Arial,sans-serif" font-size="20" font-weight="700">Lewis&#39;s GitHub Stats</text>'
        + "".join(rows)
    )
    return svg_document(
        "Lewis's GitHub stats",
        "Counts of public repositories, stars, forks, and followers.",
        content,
    )


def fetch_language_totals(repositories: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    source_repositories = [
        repo for repo in repositories if not repo["fork"] and not repo["archived"]
    ]
    for repo in source_repositories:
        languages = api_get(repo["languages_url"])
        if not isinstance(languages, dict):
            raise RuntimeError(
                f"GitHub API returned an unexpected languages response for {repo['name']}."
            )
        for language, byte_count in languages.items():
            totals[language] = totals.get(language, 0) + byte_count
    return totals


def generate_languages_card(language_totals: dict[str, int]) -> str:
    ranked = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)[:5]
    total_bytes = sum(language_totals.values())
    if total_bytes:
        entries = [(name, amount) for name, amount in ranked]
        other_bytes = total_bytes - sum(amount for _, amount in entries)
        if other_bytes:
            entries.append(("Other", other_bytes))
        entries = [(name, amount, amount / total_bytes * 100) for name, amount in entries]
    else:
        entries = []

    content = [
        '<text x="36" y="49" fill="#f8fafc" font-family="Segoe UI,Arial,sans-serif" font-size="20" font-weight="700">Most Used Languages</text>'
    ]
    if not entries:
        content.append(
            '<text x="36" y="112" fill="#cbd5e1" font-family="Segoe UI,Arial,sans-serif" font-size="14">No language data available yet.</text>'
        )
    else:
        x = 36
        bar_y = 76
        bar_width = 428
        for index, (_, _, percentage) in enumerate(entries):
            segment_width = bar_width * percentage / 100
            content.append(
                f'<rect x="{x:.2f}" y="{bar_y}" width="{segment_width:.2f}" height="12" fill="{COLORS[index]}" />'
            )
            x += segment_width
        content.append(
            f'<rect x="36" y="{bar_y}" width="{bar_width}" height="12" rx="6" fill="none" stroke="#334155" stroke-width="1"/>'
        )

        for index, (language, _, percentage) in enumerate(entries):
            column_x = 42 + (index % 2) * 218
            row_y = 121 + (index // 2) * 35
            content.append(
                f'<circle cx="{column_x}" cy="{row_y - 4}" r="6" fill="{COLORS[index]}"/>'
                f'<text x="{column_x + 14}" y="{row_y}" fill="#e2e8f0" font-family="Segoe UI,Arial,sans-serif" font-size="13">{escape(language)} {percentage:.1f}%</text>'
            )

    return svg_document(
        "Most-used programming languages",
        "Top five languages and other code by bytes across original, non-archived repositories.",
        "".join(content),
    )


def main() -> None:
    user = api_get(f"{API_BASE}/users/{USERNAME}")
    repositories = fetch_repositories()
    language_totals = fetch_language_totals(repositories)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "github-stats.svg").write_text(
        generate_stats_card(user, repositories), encoding="utf-8"
    )
    (OUTPUT_DIR / "top-languages.svg").write_text(
        generate_languages_card(language_totals), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
