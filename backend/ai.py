"""Текст запроса -> программа постройки.

Работает через OpenAI-совместимый endpoint NVIDIA NIM, поэтому сменить
провайдера можно одним `LLM_BASE_URL` + `LLM_MODEL` в `.env`.

Схему и палитру модели не пересказываем руками: берём их из
builder/schema.py и builder/blocks.py — один источник правды.

Запуск:
    python -m backend.ai "Golden Gate Bridge"
    python -m backend.ai "маяк" --build          # сгенерировать и построить
    python -m backend.ai "дракон" --model openai/gpt-oss-20b
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from pydantic import ValidationError

from builder.blocks import palette_for_prompt
from builder.schema import BuildProgram, schema_for_prompt

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
DEFAULT_FALLBACK_MODEL = "openai/gpt-oss-20b"
DEFAULT_TIMEOUT = 150.0
# Модели-«рассуждатели» тратят тысячи токенов на размышления. С маленьким
# лимитом JSON обрывается на середине — это и выглядело как «битый JSON».
DEFAULT_MAX_TOKENS = 16000

# Что-то длинное (мост, стена, дорога) не влезает в куб 40x40x40
BIG_SIZE_LIMIT = 110
BIG_WORDS = (
    "мост", "bridge", "стена", "wall", "дорога", "road", "виадук",
    "golden gate", "акведук", "aqueduct", "поезд", "train", "туннель",
    "tunnel", "канал", "canal", "забор", "runway", "полоса",
)


class LLMError(RuntimeError):
    """Модель не ответила или не смогла выдать валидную программу."""


# --- промпт --------------------------------------------------------------

# Два примера: учат ставить силуэт раньше деталей и вырезать окна блоком air.
EXAMPLES = """\
Request: "маяк"
{"name":"Маяк","size":[13,30,13],"parts":[
{"type":"cylinder","center":[6,0,6],"radius":6,"height":2,"block":"stone_bricks"},
{"type":"cylinder","center":[6,2,6],"radius":5,"height":20,"hollow":true,"block":"white_concrete"},
{"type":"cylinder","center":[6,8,6],"radius":5,"height":3,"hollow":true,"block":"red_concrete"},
{"type":"box","from":[5,2,1],"to":[7,5,1],"block":"air"},
{"type":"cylinder","center":[6,22,6],"radius":6,"height":1,"block":"gray_concrete"},
{"type":"cylinder","center":[6,23,6],"radius":4,"height":4,"hollow":true,"block":"glass"},
{"type":"sphere","center":[6,25,6],"radius":2,"block":"glowstone"},
{"type":"roof","from":[2,28,2],"to":[10,28,10],"style":"pyramid","block":"red_concrete"}]}

Request: "small house"
{"name":"Small house","size":[11,9,11],"parts":[
{"type":"box","from":[0,0,0],"to":[10,0,10],"block":"stone_bricks"},
{"type":"hollow_box","from":[0,1,0],"to":[10,6,10],"block":"oak_planks"},
{"type":"box","from":[4,1,0],"to":[6,4,0],"block":"air"},
{"type":"box","from":[0,3,3],"to":[0,5,7],"block":"glass"},
{"type":"box","from":[10,3,3],"to":[10,5,7],"block":"glass"},
{"type":"roof","from":[0,7,0],"to":[10,7,10],"style":"gable","block":"dark_oak_planks"}]}\
"""


def system_prompt(size_limit: int) -> str:
    """Системный промпт: схема, палитра, правила, примеры."""
    return f"""You convert a short request into a Minecraft build program.

PRIMITIVES (this is the only geometry you may use):
{schema_for_prompt()}

ALLOWED BLOCKS — use ONLY ids from this list:
{palette_for_prompt()}

RULES
1. Reply with ONE JSON object and nothing else. No markdown, no comments.
2. Shape: {{"name": str, "size": [w, h, d], "parts": [part, ...]}}
3. "name" is a short title in the same language as the request.
4. Coordinates are relative to the build point: x right, y up, z forward.
   y=0 is ground level. Never use negative y.
5. "size" must be the real bounding box of your parts and must fit in
   {size_limit}x{size_limit}x{size_limit}.
6. 8 to 25 parts. Build the silhouette first (big shapes), then details.
7. Parts are drawn in order; a later part overwrites an earlier one.
   Carve windows and doors with a part whose block is "air".
8. Make it recognizable from a distance: right proportions and contrasting
   materials matter more than small decorations.
9. Do not compute block lists yourself — only primitives.

EXAMPLES
{EXAMPLES}"""


def size_limit_for(text: str) -> int:
    """Мост и прочее длинное не влезает в 40 блоков — поднимаем предел."""
    low = text.lower()
    return BIG_SIZE_LIMIT if any(w in low for w in BIG_WORDS) else 40


# --- разбор ответа -------------------------------------------------------

def extract_json(text: str) -> dict[str, Any]:
    """Достаёт JSON из ответа модели.

    Модели-«рассуждатели» добавляют <think>…</think>, другие оборачивают
    ответ в ```json. Убираем и то и другое, затем берём внешние скобки.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise LLMError(f"в ответе нет JSON: {text[:200]}")
    return json.loads(text[start:end + 1])


# --- вызов модели --------------------------------------------------------

def _chat(messages: list[dict], model: str, base_url: str, api_key: str,
          timeout: float, temperature: float,
          max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Один запрос к OpenAI-совместимому endpoint."""
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    if response.status_code != 200:
        raise LLMError(f"{model}: HTTP {response.status_code} {response.text[:200]}")
    choice = response.json()["choices"][0]
    message = choice["message"]
    # у некоторых моделей текст лежит в reasoning_content
    content = message.get("content") or message.get("reasoning_content") or ""
    if not content.strip():
        raise LLMError(f"{model}: пустой ответ")
    if choice.get("finish_reason") == "length":
        raise LLMError(f"{model}: ответ обрезан по лимиту токенов "
                       f"({max_tokens}) — JSON не дописан")
    return content


def _generate_with(model: str, text: str, limit: int, base_url: str,
                   api_key: str, timeout: float, retries: int,
                   temperature: float, max_tokens: int) -> BuildProgram:
    """Одна модель: попытка + разбор + повтор с текстом ошибки."""
    messages = [
        {"role": "system", "content": system_prompt(limit)},
        {"role": "user", "content": text.strip()[:300]},
    ]
    last_error = ""
    for attempt in range(retries + 1):
        content = _chat(messages, model, base_url, api_key, timeout,
                        temperature, max_tokens)
        try:
            program = BuildProgram.model_validate(extract_json(content))
        except (ValidationError, LLMError, json.JSONDecodeError, ValueError) as e:
            last_error = str(e)[:700]
        else:
            real = program.real_size()
            if all(a <= limit for a in real):
                program.size = real      # заявленному size от LLM не верим
                return program
            last_error = (f"настоящие габариты {list(real)} не влезают в "
                          f"предел {limit}; уменьши постройку")
        if attempt < retries:
            # возвращаем модели её же ответ и ошибку — пусть починит
            messages += [
                {"role": "assistant", "content": content[:4000]},
                {"role": "user", "content":
                    f"Your JSON was rejected: {last_error}\n"
                    f"Reply with the corrected JSON object only."},
            ]
    raise LLMError(f"{model}: {last_error}")


def generate(
    text: str,
    size_limit: int | None = None,
    model: str | None = None,
    retries: int = 1,
    temperature: float = 0.4,
) -> BuildProgram:
    """Запрос человека -> проверенная программа постройки.

    Сначала основная модель (с одним повтором на исправление ошибки),
    если совсем не вышло — запасная. В зале лучше построить что-то похуже,
    чем ничего.
    """
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise LLMError("нет ключа: заполни NVIDIA_API_KEY в .env")
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    timeout = float(os.getenv("LLM_TIMEOUT", DEFAULT_TIMEOUT))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS))
    limit = size_limit or size_limit_for(text)

    chain = [model] if model else [
        os.getenv("LLM_MODEL", DEFAULT_MODEL),
        os.getenv("LLM_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
    ]

    errors = []
    for name in chain:
        try:
            return _generate_with(name, text, limit, base_url, api_key,
                                  timeout, retries, temperature, max_tokens)
        except (LLMError, requests.RequestException) as e:
            errors.append(str(e)[:300])
    raise LLMError("ни одна модель не справилась: " + " | ".join(errors))


# --- командная строка ----------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    ap = argparse.ArgumentParser(description="Текст -> программа постройки")
    ap.add_argument("text", help="что построить")
    ap.add_argument("--model", help="переопределить LLM_MODEL")
    ap.add_argument("--limit", type=int, help="предел размера, блоков")
    ap.add_argument("--out", help="куда сохранить JSON (по умолчанию programs/)")
    ap.add_argument("--build", action="store_true", help="сразу построить в игре")
    ap.add_argument("--surface", action="store_true",
                    help="искать землю по карте высот (обычный мир)")
    ap.add_argument("--duration", type=float, default=10.0,
                    help="за сколько секунд построить")
    args = ap.parse_args(argv)

    started = time.time()
    program = generate(args.text, size_limit=args.limit, model=args.model)
    print(f"«{program.name}»: {len(program.parts)} частей, size={list(program.size)}, "
          f"{round(time.time() - started, 1)} сек")

    slug = re.sub(r"[^a-z0-9а-я]+", "_", args.text.lower())[:40].strip("_")
    out = Path(args.out or f"programs/{slug or 'program'}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(program.model_dump(by_alias=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"сохранено: {out}")

    if args.build:
        from builder.build import build, make_editor, origin_near_player

        ground = "surface" if args.surface else int(os.getenv("GROUND_Y", -60))
        origin = origin_near_player(
            ground_y=ground, footprint=(program.size[0], program.size[2])
        )
        print(f"строю в {origin} …")
        report = build(program, origin, editor=make_editor(),
                       duration=args.duration, clear=True)
        print(f"готово: {report['blocks']} блоков, {report['seconds']} сек")


if __name__ == "__main__":
    main()
