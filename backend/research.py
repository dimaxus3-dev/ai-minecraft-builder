"""Справка о здании из Википедии: чтобы модель знала, как оно выглядит (форма, высота, цвета,
материалы), а не угадывала по названию. Язык выбираем по письму запроса; при любой ошибке
возвращаем None, и генерация идёт как раньше."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "ai-minecraft-builder/1.0 (hackathon project; https://github.com/dimaxus3-dev/ai-minecraft-builder)"}


def languages_for(text: str) -> list[str]:
    low = text.lower()
    if re.search("[іїєґ]", low):
        return ["uk", "en"]
    if re.search("[әңғүұқөһ]", low):
        return ["kk", "ru", "en"]
    if re.search("[а-я]", low):
        return ["ru", "en"]
    return ["en"]


def facts(query: str, timeout: float = 3.5, chars: int = 900) -> str | None:
    """Первые абзацы статьи, если нашлась статья именно про это. Иначе None."""
    q = re.sub(r"\s+", " ", query).strip()[:120]
    if len(q) < 3:
        return None
    words = [w[:5] for w in re.findall(r"\w{4,}", q.lower())]
    for lang in languages_for(q):
        url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&generator=search"
               f"&gsrsearch={urllib.parse.quote(q)}&gsrlimit=1&prop=extracts&exintro=1&explaintext=1"
               f"&exchars={chars}&redirects=1&format=json&formatversion=2")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                pages = json.load(r).get("query", {}).get("pages", [])
        except Exception:
            continue
        if not pages:
            continue
        title = pages[0].get("title", "")
        extract = re.sub(r"\s+", " ", pages[0].get("extract") or "").strip()
        if len(extract) < 80:
            continue
        # статья должна быть про то же: хотя бы один корень слова запроса есть в заголовке
        if words and not any(w in title.lower() for w in words):
            continue
        return f"{title} ({lang}.wikipedia): {extract}"
    return None
