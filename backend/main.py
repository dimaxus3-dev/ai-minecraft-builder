"""FastAPI: сайт для людей, админка, экран зала и мост до воркера.

Поток одного запроса:
    человек пишет текст          -> pending
    я нажимаю ✅ в админке        -> approved
    сервер зовёт LLM             -> generating
    воркер строит в Minecraft    -> building -> done

Воркер сам подключается к нам по WebSocket, поэтому неважно, какой на
месте Wi-Fi: входящие соединения к ноутбуку не нужны.

Запуск локально:
    ./venv/bin/python -m uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from . import ai, queue_db as db          # noqa: E402

log = logging.getLogger("hack")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "dev")
WORKER_SECRET = os.getenv("WORKER_SECRET", ADMIN_SECRET)
RATE_LIMIT = int(os.getenv("RATE_LIMIT_SECONDS", 60))
BUILD_TIMEOUT = float(os.getenv("BUILD_TIMEOUT", 300))
GENERATE_TIMEOUT = float(os.getenv("GENERATE_TIMEOUT", 200))


# --- рассылка по WebSocket ----------------------------------------------

class Hub:
    """Держит открытые сокеты страниц и рассылает им события."""

    def __init__(self) -> None:
        self.channels: dict[str, set[WebSocket]] = {
            "public": set(), "admin": set(), "screen": set(),
        }

    async def join(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        self.channels[channel].add(ws)

    def leave(self, channel: str, ws: WebSocket) -> None:
        self.channels[channel].discard(ws)

    async def send(self, event: dict, channels: tuple[str, ...] =
                   ("public", "admin", "screen")) -> None:
        """Отправляем всем и молча выкидываем отвалившиеся сокеты."""
        dead: list[tuple[str, WebSocket]] = []
        for channel in channels:
            for ws in tuple(self.channels[channel]):
                try:
                    await ws.send_json(event)
                except Exception:
                    dead.append((channel, ws))
        for channel, ws in dead:
            self.leave(channel, ws)


hub = Hub()


class Worker:
    """Единственный воркер-строитель. Побеждает последний подключившийся."""

    def __init__(self) -> None:
        self.ws: WebSocket | None = None
        self.busy = False

    @property
    def online(self) -> bool:
        return self.ws is not None

    async def send(self, payload: dict) -> bool:
        if self.ws is None:
            return False
        try:
            await self.ws.send_json(payload)
            return True
        except Exception:
            self.ws = None
            return False


worker = Worker()


async def announce(request_row: dict | None = None, **extra) -> None:
    """Одно место, которое шлёт страницам свежее состояние."""
    event = {"type": "update", "stats": db.stats(),
             "worker_online": worker.online, **extra}
    if request_row is not None:
        event["request"] = request_row
    await hub.send(event)


# --- обработка очереди ---------------------------------------------------

# Чертёж готовим сразу при отправке запроса, пока он ждёт одобрения. Тогда
# после «✅» постройка стартует мгновенно, а не через полминуты ожидания LLM.
pregen: dict[int, asyncio.Task] = {}
pregen_slots = asyncio.Semaphore(3)       # не заваливаем API, если пишут разом


async def pregenerate(request_id: int, text: str) -> None:
    """Фоновая генерация чертежа. Ошибки молча глотаем: после одобрения
    run_job всё равно сгенерирует заново."""
    try:
        async with pregen_slots:
            program = await asyncio.wait_for(
                asyncio.to_thread(ai.generate, text), timeout=GENERATE_TIMEOUT)
        current = db.get(request_id)
        # кладём чертёж, только если текст не меняли и запрос не отклонили
        if current and current["text"] == text and current["status"] != db.REJECTED:
            db.set_program(request_id, program.model_dump(by_alias=True))
            log.info("#%s: чертёж готов заранее (%s)", request_id, program.name)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.info("#%s: предгенерация не вышла (%s), сделаем после одобрения",
                 request_id, type(e).__name__)
    finally:
        if pregen.get(request_id) is asyncio.current_task():
            pregen.pop(request_id, None)


def start_pregen(request_id: int, text: str) -> None:
    pregen[request_id] = asyncio.create_task(pregenerate(request_id, text))


def cancel_pregen(request_id: int) -> None:
    task = pregen.pop(request_id, None)
    if task and not task.done():
        task.cancel()


async def get_program(row: dict) -> dict:
    """Чертёж запроса: готовый, из идущей предгенерации или заново."""
    request_id = row["id"]
    if row.get("program"):
        return row["program"]
    task = pregen.get(request_id)
    if task and not task.done():
        await asyncio.shield(task)        # сама ошибок не бросает
        fresh = db.get(request_id)
        if fresh and fresh.get("program"):
            return fresh["program"]
    program = await asyncio.to_thread(ai.generate, row["text"])
    payload = program.model_dump(by_alias=True)
    db.set_program(request_id, payload)
    return payload


async def run_job(row: dict) -> None:
    """Один запрос: LLM -> воркер -> ждём результат."""
    request_id = row["id"]
    worker.busy = True
    try:
        if not row.get("program"):          # заготовки нет — придётся ждать LLM
            await announce(db.set_status(request_id, db.GENERATING))
        try:
            payload = await asyncio.wait_for(get_program(row),
                                             timeout=GENERATE_TIMEOUT)
        except asyncio.TimeoutError:
            reason = f"LLM не ответил за {GENERATE_TIMEOUT:.0f} с"
            log.warning("#%s: %s", request_id, reason)
            await announce(db.set_status(request_id, db.FAILED, reason))
            return
        except Exception as e:
            log.warning("LLM не справился с #%s: %s", request_id, e)
            await announce(db.set_status(request_id, db.FAILED,
                                         f"{type(e).__name__}: {e}"))
            return

        if not await worker.send({"type": "build", "id": request_id,
                                  "text": row["text"], "program": payload}):
            # воркер отвалился между проверкой и отправкой — вернём в очередь
            await announce(db.set_status(request_id, db.APPROVED))
            return

        await announce(db.set_status(request_id, db.BUILDING))

        # ждём, пока воркер отчитается; если умер — не держим очередь
        deadline = asyncio.get_event_loop().time() + BUILD_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.5)
            current = db.get(request_id)
            if current and current["status"] not in db.ACTIVE:
                return
        await announce(db.set_status(request_id, db.FAILED,
                                     "воркер не ответил вовремя"))
    finally:
        worker.busy = False


async def pump() -> None:
    """Фоновая петля: берёт одобренные запросы по одному."""
    while True:
        try:
            if worker.online and not worker.busy:
                row = db.next_approved()
                if row:
                    await run_job(row)
        except Exception:
            log.exception("петля очереди споткнулась")
        await asyncio.sleep(1)


# --- приложение ----------------------------------------------------------

app = FastAPI(title="AI Minecraft Builder")

if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
async def on_startup() -> None:
    db.connect()
    # после перезапуска сервера незавершённые стройки возвращаем в очередь
    for row in db.stuck_active():
        if row["status"] != db.APPROVED:
            db.set_status(row["id"], db.APPROVED)
    asyncio.create_task(pump())
    log.info("админка: /admin-%s", ADMIN_SECRET)


def page(name: str, fallback: str) -> HTMLResponse:
    """Отдаём файл напарника, если он уже есть, иначе простую заглушку."""
    path = STATIC / name
    if path.exists():
        return HTMLResponse(path.read_text(encoding="utf-8"))
    return HTMLResponse(fallback)


FALLBACK_INDEX = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Что построить?</title>
<body style="font:16px system-ui;max-width:28rem;margin:3rem auto;padding:1rem">
<h1>Что построить в Minecraft?</h1>
<form onsubmit="send(event)">
  <input id=t placeholder="маяк, дракон, Golden Gate…" required
         style="width:100%;padding:.8rem;font-size:1rem">
  <button style="margin-top:.6rem;padding:.8rem 1.2rem;font-size:1rem">
    Отправить</button>
</form>
<p id=s></p>
<script>
async function send(e){e.preventDefault();
  const r=await fetch('/api/request',{method:'POST',
    headers:{'content-type':'application/json'},
    body:JSON.stringify({text:t.value})});
  const d=await r.json();
  s.textContent=r.ok?'Запрос #'+d.id+' отправлен на модерацию':d.detail;}
new WebSocket(location.origin.replace('http','ws')+'/ws/public')
  .onmessage=m=>{const d=JSON.parse(m.data);
    if(d.request)s.textContent='#'+d.request.id+': '+d.request.status;};
</script>"""

FALLBACK_SCREEN = """<!doctype html><meta charset=utf-8><title>Экран</title>
<body style="font:20px system-ui;background:#111;color:#eee;padding:2rem">
<h1 id=h>Ждём запросы…</h1><pre id=q></pre>
<script>
new WebSocket(location.origin.replace('http','ws')+'/ws/screen')
  .onmessage=m=>{const d=JSON.parse(m.data);
    if(d.stats)h.textContent='Построено: '+d.stats.built+
      ' | в очереди: '+d.stats.waiting+' | блоков: '+d.stats.blocks;
    if(d.request)q.textContent='#'+d.request.id+' '+d.request.text+
      ' → '+d.request.status;};
</script>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return page("index.html", FALLBACK_INDEX)


@app.get("/screen", response_class=HTMLResponse)
async def screen() -> HTMLResponse:
    return page("screen.html", FALLBACK_SCREEN)


@app.get("/admin-{secret}", response_class=HTMLResponse)
async def admin(secret: str) -> HTMLResponse:
    if secret != ADMIN_SECRET:
        raise HTTPException(404)
    return page("admin.html", "<h1>static/admin.html ещё не готов</h1>")


# --- API для людей -------------------------------------------------------

@app.post("/api/request")
async def api_request(request: Request) -> JSONResponse:
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not 2 <= len(text) <= 300:
        raise HTTPException(400, "Напиши от 2 до 300 символов")

    ip = request.client.host if request.client else ""
    if RATE_LIMIT and ip:
        last = db.last_from_ip(ip)
        if last:
            age = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(last["created_at"])).total_seconds()
            if age < RATE_LIMIT:
                raise HTTPException(
                    429, f"Подожди {int(RATE_LIMIT - age)} сек перед новым запросом")

    row = db.add(text, author=(body.get("author") or "")[:40], ip=ip)
    start_pregen(row["id"], row["text"])
    await announce(row)
    return JSONResponse(row)


@app.get("/api/requests")
async def api_requests() -> dict:
    return {"requests": db.recent(), "stats": db.stats(),
            "worker_online": worker.online}


# --- API админки ---------------------------------------------------------

def check_secret(secret: str) -> None:
    if secret != ADMIN_SECRET:
        raise HTTPException(404)


@app.post("/api/admin/{secret}/{request_id}/approve")
async def api_approve(secret: str, request_id: int) -> dict:
    check_secret(secret)
    row = db.get(request_id)
    if not row:
        raise HTTPException(404, "нет такого запроса")
    if row["status"] not in (db.PENDING, db.FAILED, db.REJECTED):
        return row        # уже одобрен или строится: повторный клик ничего не ломает
    row = db.set_status(request_id, db.APPROVED)
    await announce(row)
    return row                                        # type: ignore[return-value]


@app.post("/api/admin/{secret}/{request_id}/reject")
async def api_reject(secret: str, request_id: int) -> dict:
    check_secret(secret)
    cancel_pregen(request_id)
    row = db.set_status(request_id, db.REJECTED)
    if not row:
        raise HTTPException(404, "нет такого запроса")
    await announce(row)
    return row


@app.post("/api/admin/{secret}/{request_id}/text")
async def api_edit(secret: str, request_id: int, request: Request) -> dict:
    """Правка текста перед одобрением."""
    check_secret(secret)
    body = await request.json()
    row = db.update_text(request_id, (body.get("text") or "").strip())
    if not row:
        raise HTTPException(404, "нет такого запроса")
    if row["status"] == db.PENDING:
        cancel_pregen(request_id)
        row = db.clear_program(request_id)
        start_pregen(request_id, row["text"])             # type: ignore[index]
    await announce(row)
    return row


# --- WebSocket -----------------------------------------------------------

async def page_socket(channel: str, ws: WebSocket) -> None:
    await hub.join(channel, ws)
    try:
        await ws.send_json({"type": "init", "requests": db.recent(),
                            "stats": db.stats(), "worker_online": worker.online})
        while True:                      # страницы только слушают
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        hub.leave(channel, ws)


@app.websocket("/ws/public")
async def ws_public(ws: WebSocket) -> None:
    await page_socket("public", ws)


@app.websocket("/ws/admin")
async def ws_admin(ws: WebSocket) -> None:
    await page_socket("admin", ws)


@app.websocket("/ws/screen")
async def ws_screen(ws: WebSocket) -> None:
    await page_socket("screen", ws)


@app.websocket("/ws/worker")
async def ws_worker(ws: WebSocket) -> None:
    """Сюда подключается ноутбук с Minecraft."""
    if ws.query_params.get("secret") != WORKER_SECRET:
        await ws.close(code=4003)
        return
    await ws.accept()
    worker.ws = ws
    log.info("воркер подключился")
    await announce()
    try:
        while True:
            message = json.loads(await ws.receive_text())
            kind = message.get("type")
            request_id = message.get("id")

            if kind == "progress":
                await hub.send({"type": "progress", "id": request_id,
                                "done": message.get("done"),
                                "total": message.get("total")})
            elif kind == "done":
                db.set_result(request_id, message.get("origin") or [],
                              int(message.get("blocks") or 0))
                await announce(db.set_status(request_id, db.DONE))
                log.info("#%s построен: %s блоков", request_id,
                         message.get("blocks"))
            elif kind == "failed":
                await announce(db.set_status(request_id, db.FAILED,
                                             str(message.get("error"))[:400]))
                log.warning("#%s не построился: %s", request_id,
                            message.get("error"))
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("сокет воркера упал")
    finally:
        if worker.ws is ws:
            worker.ws = None
        log.info("воркер отключился")
        await announce()
