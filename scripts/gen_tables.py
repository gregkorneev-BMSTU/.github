#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import urllib.request
from dataclasses import dataclass
from typing import List, Tuple

START_LABS = "<!-- AUTOGEN:S2_LABS:START -->"
END_LABS   = "<!-- AUTOGEN:S2_LABS:END -->"
START_SEMS = "<!-- AUTOGEN:S2_SEMS:START -->"
END_SEMS   = "<!-- AUTOGEN:S2_SEMS:END -->"

LAB_PREFIX = "s2_lab"
SEM_PREFIX = "s2_sem"

@dataclass
class Repo:
    name: str
    html_url: str
    description: str

def gh_api_get(url: str, token: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def list_org_repos(org: str, token: str) -> List[Repo]:
    repos: List[Repo] = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}&type=all&sort=full_name&direction=asc"
        data = gh_api_get(url, token)
        if not isinstance(data, list) or len(data) == 0:
            break
        for r in data:
            name = r.get("name") or ""
            html_url = r.get("html_url") or ""
            desc = r.get("description") or ""
            if name and html_url:
                repos.append(Repo(name=name, html_url=html_url, description=desc))
        page += 1
    return repos

def extract_num(repo_name: str, prefix: str) -> Tuple[int, str]:
    # Поддерживает: s2_lab01, s2_lab1, s2_lab02_var21, s2_sem10-part1, s2_sem3_topic
    tail = repo_name[len(prefix):]
    m = re.search(r"(\d+)", tail)
    if m:
        n = int(m.group(1))
    else:
        n = 10**9  # если числа нет — уедет в конец
    return n, tail

def title_from_repo(repo: Repo) -> str:
    # Если у репозитория заполнено Description — используем его как "человеческое" название.
    t = (repo.description or "").strip()
    return t if t else repo.name

def make_rows(repos: List[Repo], prefix: str) -> str:
    items = []
    for r in repos:
        if r.name.startswith(prefix):
            n, _ = extract_num(r.name, prefix)
            items.append((n, r.name.lower(), r))
    items.sort(key=lambda x: (x[0], x[1]))

    lines = []
    for n, _, repo in items:
        display_n = "" if n == 10**9 else str(n)
        title = title_from_repo(repo)
        lines.append(
            f'<tr><td>{display_n}</td><td>{title}</td><td><a href="{repo.html_url}">Открыть</a></td></tr>'
        )
    if not lines:
        lines.append('<tr><td colspan="3"><i>Пока нет репозиториев с этим префиксом</i></td></tr>')
    return "\n".join(lines)

def replace_block(text: str, start: str, end: str, new_inner: str) -> str:
    if start not in text or end not in text:
        raise RuntimeError(f"Не найдены маркеры блока: {start} ... {end}")
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    replacement = start + "\n" + new_inner + "\n" + end
    return pattern.sub(replacement, text, count=1)

def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    org = os.environ.get("GITHUB_ORG", "").strip()
    readme_path = os.environ.get("README_PATH", "README.md").strip()

    if not token:
        print("ERROR: GITHUB_TOKEN is empty", file=sys.stderr)
        return 2
    if not org:
        print("ERROR: GITHUB_ORG is empty", file=sys.stderr)
        return 2

    repos = list_org_repos(org, token)

    labs_rows = make_rows(repos, LAB_PREFIX)
    sems_rows = make_rows(repos, SEM_PREFIX)

    with open(readme_path, "r", encoding="utf-8") as f:
        md = f.read()

    md = replace_block(md, START_LABS, END_LABS, labs_rows)
    md = replace_block(md, START_SEMS, END_SEMS, sems_rows)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(md)

    print("README updated.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
