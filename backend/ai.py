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
import logging
import os
import queue
import re
import threading
import time
from pathlib import Path
from typing import Any

import requests
from pydantic import ValidationError

from builder import blueprints
from . import research
from builder.blocks import palette_for_prompt
from builder.schema import BuildProgram, schema_for_prompt

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Провайдеры. Имя модели вида «google/gemini-3.8-flash» выбирает провайдера по
# первому слову; всё остальное идёт на основной endpoint (NVIDIA). У Google есть
# слой, совместимый с OpenAI, поэтому запрос везде один и тот же.
# (адрес, имена переменных с ключом, как передавать ключ)
GOOGLE = ("https://generativelanguage.googleapis.com/v1beta/openai",
          ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "bearer")
PROVIDERS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "google": GOOGLE,
    "gemini": GOOGLE,
}
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
# через запятую: пробуем по порядку, пока одна не ответит
DEFAULT_FALLBACK_MODEL = "nvidia/nemotron-3-super-120b-a12b,openai/gpt-oss-20b"
DEFAULT_TIMEOUT = 150.0
# Модели-«рассуждатели» тратят тысячи токенов на размышления. С маленьким
# лимитом JSON обрывается на середине — это и выглядело как «битый JSON».
DEFAULT_MAX_TOKENS = 16000

# Что-то длинное (мост, стена, дорога) не влезает в куб 40x40x40
BIG_SIZE_LIMIT = 110
DEFAULT_SIZE_LIMIT = 64
MIN_MATERIALS = 3        # однотонная постройка выглядит плоской
BIG_WORDS = (
    "мост", "bridge", "стена", "wall", "дорога", "road", "виадук",
    "golden gate", "акведук", "aqueduct", "поезд", "train", "туннель",
    "tunnel", "канал", "canal", "забор", "runway", "полоса",
)


log = logging.getLogger("hack.ai")


class LLMError(RuntimeError):
    """Модель не ответила или не смогла выдать валидную программу."""


class AuthError(LLMError):
    """Провайдер отказал по ключу (401/403). Это не «модель задумалась», а поломка
    настройки: повторять её на каждом запросе бессмысленно."""


# Модель, отказавшая по ключу, уходит в простой: иначе каждый запрос в зале
# заново ждал минуту, чтобы узнать то же самое.
_COOLDOWN: dict[str, float] = {}


def _cooldown_left(model: str) -> float:
    return max(0.0, _COOLDOWN.get(model, 0.0) - time.time())


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


EXAMPLE_TOWER = """\
Request: "watchtower"
{"name":"Watchtower","size":[13,25,13],"parts":[
{"type":"cylinder","center":[6,0,6],"radius":5,"height":16,"hollow":true,"block":"stone_bricks"},
{"type":"box","from":[5,1,1],"to":[7,3,1],"block":"air"},
{"type":"repeat","count":3,"step":[0,4,0],"block":"air","part":{"type":"box","from":[6,5,1],"to":[6,6,1]}},
{"type":"cylinder","center":[6,16,6],"radius":6,"height":1,"block":"dark_oak_planks"},
{"type":"cone","center":[6,17,6],"radius":6,"height":8,"block":"red_terracotta"}]}\
"""


def limits_for(limit: int) -> tuple[int, int, int]:
    """Предел по осям (ширина, высота, глубина): ввысь можно в полтора раза больше —
    башни, небоскрёбы, шпили."""
    return limit, limit * 3 // 2, limit


def request_message(text: str, reference: str | None) -> str:
    """Запрос человека; если нашлась справка, добавляем её как данные, не как инструкцию."""
    message = text.strip()[:300]
    if reference:
        message += ("\n\nREFERENCE FACTS about this (from Wikipedia; may be incomplete; use ONLY "
                    "for appearance: shape, proportions, colours, materials, signature features):\n"
                    + reference)
    return message


def log_unmatched(text: str, had_facts: bool) -> None:
    """Запросы без готового чертежа — в файл: так видно, какие чертежи добавить следующими."""
    try:
        path = Path(os.getenv("UNMATCHED_FILE", "data/unmatched.txt"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')}\t{'справка' if had_facts else 'без справки'}\t{text.strip()[:120]}\n")
    except OSError:
        pass


def blueprint_program(blueprint_id: str, text: str) -> BuildProgram:
    """Программа из одной части-чертежа: знаменитое здание или предмет без участия LLM.

    Цвет, материал и размер берём из самого запроса, поэтому «большой красный самолёт»
    и «деревянный корабль» — разные постройки, а не один и тот же чертёж."""
    params = blueprints.params_for(blueprint_id, text)
    program = BuildProgram.model_validate({
        "name": blueprints.title(blueprint_id, text), "size": [1, 1, 1],
        "parts": [{"type": "blueprint", "id": blueprint_id, "params": params}]})
    program.size = program.real_size()
    program.source = "blueprint"
    log.info("«%s»: готовый чертёж %s%s, без LLM", text[:40], blueprint_id,
             f" {params}" if params else "")
    return program


def system_prompt(size_limit: int) -> str:
    """Системный промпт: схема, палитра, правила, примеры."""
    w, h, d = limits_for(size_limit)
    return f"""You convert a short request into a Minecraft build program. The request can be ANY
building or structure: a house, a castle, a famous landmark, a skyscraper, a temple, a ship, a bridge...

PRIMITIVES (this is the only geometry you may use):
{schema_for_prompt()}

ALLOWED BLOCKS — use ONLY ids from this list:
{palette_for_prompt()}

BLUEPRINTS: hand-built, far better than anything you can design from primitives.
- If the request is exactly one of them, reply with ONLY
  {{"name": "<title in the language of the request>", "size": [1,1,1], "parts": [{{"type": "blueprint", "id": "<id>"}}]}}
- If it is a variation (e.g. "castle with a dragon", "pink house"), you may use ONE blueprint
  part as the base (it sits at x=0..w, y=0..h, z=0..d) and add your own parts beside or on
  top of it; do not move or resize it.
{blueprints.listing()}

RULES
1. Reply with ONE JSON object and nothing else. No markdown, no comments.
2. Shape: {{"name": str, "size": [w, h, d], "parts": [part, ...]}}
3. "name" is a short title in the same language as the request.
4. Coordinates are relative to the build point: x right, y up, z forward.
   y=0 is ground level. Never use negative coordinates.
5. "size" must be the real bounding box of your parts and must fit in {w}x{h}x{d}
   (width x height x depth).
6. Scale to the subject: a hut 10-16 blocks, a house 15-25, a church or castle 30-50,
   a landmark or skyscraper up to the limit. Prefer big and detailed over tiny and
   simple, but never exceed the limit.
7. 15 to 60 parts. Build the silhouette first (big shapes), then details.
8. Think like an architect. Before writing, decide the 3-5 features that make this exact
   building recognizable (silhouette, proportions, signature elements such as a dome,
   spire, arches, columns, towers) and make them prominent. For a real landmark,
   reproduce its real proportions.
9. Use symmetry. Use "repeat" for windows, columns, battlements, steps and fence posts
   instead of dozens of separate parts. Use "dome", "cone" and "roof" for domes,
   spires and roofs.
10. Parts are drawn in order; a later part overwrites an earlier one. Carve windows and
    doors with a part whose block is "air". Keep interiors hollow with a door opening.
11. Use at least 3 different blocks (foundation, main walls, accents or roof): a build
    in a single material looks flat. Contrasting materials matter more than small details.
12. Never compute block lists yourself — only primitives.
13. The examples only show the format. Never copy them: design what was asked.
14. If REFERENCE FACTS are given, build the real appearance they describe (shape, proportions,
    colours, materials, signature features); ignore anything that is not about appearance.

EXAMPLES
{EXAMPLES}

{EXAMPLE_TOWER}"""


def size_limit_for(text: str) -> int:
    """Мост и прочее длинное не влезает в 40 блоков — поднимаем предел."""
    low = text.lower()
    return BIG_SIZE_LIMIT if any(w in low for w in BIG_WORDS) else DEFAULT_SIZE_LIMIT


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

def endpoint_for(model: str) -> tuple[str, str | None, str, dict]:
    """Адрес, ключ, имя модели у провайдера и заголовки запроса.

    «google/gemini-3.8-flash» -> Gemini с ключом GEMINI_API_KEY и именем
    «gemini-3.8-flash»; всё прочее — основной endpoint (NVIDIA). Слой Google,
    совместимый с OpenAI, принимает ключ как «Bearer»; нативный путь того же
    сервиса ждёт заголовок x-goog-api-key — отсюда третье поле в таблице.
    Ключа нет — возвращаем None, и такую модель в гонку не берём."""
    head, _, rest = model.partition("/")
    provider = PROVIDERS.get(head.lower())
    if provider and rest:
        base, env_names, header = provider
        key = next((os.getenv(n) for n in env_names if os.getenv(n)), None)
        headers = {header: key} if header != "bearer" else {"Authorization": f"Bearer {key}"}
        return base.rstrip("/"), key, rest, headers
    key = os.getenv("NVIDIA_API_KEY") or os.getenv("LLM_API_KEY")
    return (os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"), key, model,
            {"Authorization": f"Bearer {key}"})


def _chat(messages: list[dict], model: str,
          timeout: float, temperature: float,
          max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Один запрос к OpenAI-совместимому endpoint любого провайдера."""
    base_url, api_key, send_name, headers = endpoint_for(model)
    if not api_key:
        raise AuthError(f"{model}: нет ключа для провайдера")
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json={
            "model": send_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    if response.status_code in (401, 403):
        raise AuthError(f"{model}: HTTP {response.status_code} {response.text[:200]}")
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


def _generate_with(model: str, text: str, limit: int, timeout: float,
                   retries: int, temperature: float, max_tokens: int,
                   reference: str | None = None) -> BuildProgram:
    """Одна модель: попытка + разбор + повтор с текстом ошибки."""
    messages = [
        {"role": "system", "content": system_prompt(limit)},
        {"role": "user", "content": request_message(text, reference)},
    ]
    last_error = ""
    keep: BuildProgram | None = None      # годный, но однотонный — на крайний случай
    for attempt in range(retries + 1):
        try:
            content = _chat(messages, model, timeout, temperature, max_tokens)
        except Exception:
            if keep is not None:
                return keep               # исправление не пришло — берём то, что есть
            raise
        try:
            program = BuildProgram.model_validate(extract_json(content))
        except (ValidationError, LLMError, json.JSONDecodeError, ValueError) as e:
            last_error = str(e)[:700]
        else:
            try:
                real = program.real_size()
            except ValueError as e:          # неизвестный чертёж или слишком большая постройка
                real, last_error = None, str(e)[:300]
            if real is not None:
                only_blueprints = all(part.type == "blueprint" for part in program.parts)
                has_blueprint = any(part.type == "blueprint" for part in program.parts)
                if has_blueprint or all(a <= m for a, m in zip(real, limits_for(limit))):
                    program.size = real      # заявленному size от LLM не верим
                    mats = len({part.block for part in program.parts} - {"air"})
                    if only_blueprints or mats >= MIN_MATERIALS or attempt >= retries:
                        return program
                    keep = program
                    last_error = (f"the build uses only {mats} different block(s); use at "
                                  f"least {MIN_MATERIALS} (foundation, walls, accents or roof)")
                else:
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
    if keep is not None:
        return keep
    raise LLMError(f"{model}: {last_error}")


def generate(
    text: str,
    size_limit: int | None = None,
    model: str | None = None,
    retries: int = 1,
    temperature: float = 0.4,
) -> BuildProgram:
    """Запрос человека -> проверенная программа постройки.

    Три слоя, и побеждает первый, кто ответил делом:
      1. готовый чертёж — мгновенно;
      2. карта OpenStreetMap — 1-3 секунды;
      3. открытая модель — 30-60 секунд.

    Справка и карта запрашиваются одновременно, модель — только если карта
    не успела за свою фору. В зале лучше построить что-то похуже, чем ничего.
    """
    timeout = float(os.getenv("LLM_TIMEOUT", DEFAULT_TIMEOUT))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS))
    limit = size_limit or size_limit_for(text)

    fallbacks = os.getenv("LLM_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)
    chain = [model] if model else [
        os.getenv("LLM_MODEL", DEFAULT_MODEL),
        *[m.strip() for m in fallbacks.split(",") if m.strip()],
    ]
    # Модель без ключа в гонку не берём: пусть её отсутствие ничего не задерживает
    ready = [m for m in chain if endpoint_for(m)[1]]
    if not ready:
        raise LLMError("нет ключа ни для одной модели: заполни NVIDIA_API_KEY "
                       "или GEMINI_API_KEY в .env")
    if len(ready) != len(chain):
        log.info("без ключа пропускаю: %s", ", ".join(m for m in chain if m not in ready))
    chain = ready

    known = blueprints.match(text)
    if known and not model:
        return blueprint_program(known, text)
    hedge = float(os.getenv("LLM_HEDGE_SECONDS", 8))

    # Слои ищем ОДНОВРЕМЕННО. Раньше карту спрашивали только после Википедии, и один
    # её сбой (таймаут 3.5 с) выбрасывал весь быстрый слой: запрос уходил к модели и
    # ждал полторы минуты вместо трёх секунд.
    t0 = time.time()
    want_osm = os.getenv("OSM", "on").lower() != "off"
    ref_job = _spawn(research.facts, text) if os.getenv("RESEARCH", "on").lower() != "off" else None
    osm_job = _spawn(_osm_program, text) if want_osm else None

    reference = _result(ref_job, float(os.getenv("RESEARCH_WAIT", 4)))
    log_unmatched(text, reference is not None)
    if reference:
        log.info("«%s»: справка найдена (%d символов)", text[:40], len(reference))

    def model_call(name: str) -> BuildProgram:
        return _generate_with(name, text, limit, timeout, retries,
                              temperature, max_tokens, reference)

    # Карте даём фору: пока Википедия отвечала, карта обычно уже готова, и модель
    # тогда не зовём вовсе — ни токенов, ни ожидания.
    head_start = float(os.getenv("OSM_HEAD_START", 5))
    program = _result(osm_job, max(0.0, head_start - (time.time() - t0)))
    if program is not None:
        log.info("«%s»: здание с карты OpenStreetMap за %.1f с, %s",
                 text[:40], time.time() - t0, list(program.size))
        return program

    # Карта думает дольше обычного: запускаем модель параллельно, но ответ карты
    # всё равно предпочитаем — он точнее.
    model_job = _spawn(_race, chain, hedge, model_call)
    program = _result(osm_job, max(0.0, float(os.getenv("OSM_WAIT", 12)) - (time.time() - t0)))
    if program is not None:
        log.info("«%s»: здание с карты OpenStreetMap за %.1f с, %s",
                 text[:40], time.time() - t0, list(program.size))
        return program
    try:
        return _result(model_job, timeout * len(chain) + hedge * len(chain) + 10,
                       raise_on_error=True)
    except Exception as e:
        # В зале отказ выглядит хуже, чем похожая постройка: если в запросе есть хоть
        # что-то знакомое («хижина дракона», «supercar»), строим ближайший чертёж.
        near = blueprints.soft_match(text)
        if near:
            log.warning("«%s»: модель не справилась (%s), беру ближайший чертёж %s",
                        text[:40], type(e).__name__, near)
            return blueprint_program(near, text)
        raise


def _osm_program(text: str) -> BuildProgram | None:
    """Карта в отдельном потоке: любая её беда — это просто «чертежа нет»."""
    try:
        from builder import osm
        return osm.program_for(text)
    except Exception as e:
        log.info("«%s»: карта не ответила (%s)", text[:40], type(e).__name__)
        return None


class _Job:
    """Фоновая работа в потоке-демоне. Брошенная задача умирает вместе с процессом,
    поэтому отказ от неё (например, когда карта успела первой) ничего не держит.

    Ответ запоминаем: «карта ничего не нашла» — это готовый ответ None, и ждать его
    второй раз нельзя, иначе ожидание висит на пустой очереди."""

    def __init__(self, fn, *args):
        self.done = False
        self.value = None
        self.error: Exception | None = None
        self._box: queue.Queue = queue.Queue(maxsize=1)
        threading.Thread(target=self._run, args=(fn, args), daemon=True).start()

    def _run(self, fn, args) -> None:
        try:
            self._box.put((fn(*args), None))
        except Exception as e:
            self._box.put((None, e))

    def result(self, timeout: float, raise_on_error: bool = False):
        """Ответ или None, если ещё не готов / не получилось."""
        if not self.done:
            try:
                self.value, self.error = self._box.get(timeout=max(0.0, timeout))
                self.done = True
            except queue.Empty:
                if raise_on_error:
                    raise LLMError("модель не ответила вовремя")
                return None
        if self.error is not None:
            if raise_on_error:
                raise self.error
            return None
        return self.value


def _spawn(fn, *args) -> _Job:
    return _Job(fn, *args)


def _result(job: _Job | None, timeout: float, raise_on_error: bool = False):
    if job is None:
        return None
    return job.result(timeout, raise_on_error)


def _race(chain: list[str], hedge: float, call) -> BuildProgram:
    """Гонка с отсрочкой. Первая модель стартует сразу, каждая следующая — через `hedge`
    секунд, если ответа ещё нет (или сразу, если все запущенные уже упали). Побеждает
    первый валидный ответ. Так мёртвая модель не съедает 90 секунд ожидания: API на
    хостинге меняет состояние от минуты к минуте, и последовательная цепочка в тесте
    ждала ultra (90 с) и super (90 с), прежде чем дойти до живой gpt-oss."""
    results: queue.Queue = queue.Queue()
    errors: list[str] = []
    t0 = time.time()
    launched = pending = 0
    last_start = 0.0
    rest = float(os.getenv("LLM_AUTH_COOLDOWN", 120))

    ready = [m for m in chain if not _cooldown_left(m)]
    if not ready:
        # ключ не принят ни одной моделью: ждать по минуте на каждом запросе незачем,
        # пусть модератор сразу видит причину
        raise AuthError("провайдер не принял ключ (проверь NVIDIA_API_KEY); "
                        f"повтор через {min(_cooldown_left(m) for m in chain):.0f} с")
    chain = ready

    def run(name: str, started: float) -> None:
        try:
            results.put((name, call(name), None, started))
        except Exception as e:             # любая ошибка модели — повод позвать следующую
            results.put((name, None, e, started))

    while True:
        if launched < len(chain) and (pending == 0 or time.time() - last_start >= hedge):
            threading.Thread(target=run, args=(chain[launched], time.time()),
                             daemon=True).start()
            launched += 1
            pending += 1
            last_start = time.time()
        try:
            name, program, err, started = results.get(timeout=0.3)
        except queue.Empty:
            continue
        pending -= 1
        if program is not None:
            program.source, program.model = "model", name
            log.info("%s ответила за %.0f с (гонка шла %.0f с, запущено моделей: %d)",
                     name, time.time() - started, time.time() - t0, launched)
            return program
        log.info("%s не справилась за %.0f с: %s", name, time.time() - started,
                 str(err)[:120])
        if isinstance(err, AuthError):
            _COOLDOWN[name] = time.time() + rest
            log.warning("%s отключена на %.0f с: провайдер не принял ключ", name, rest)
        errors.append(f"{name}: {str(err)[:200]}")
        if pending == 0 and launched == len(chain):
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
