"""Воркер-строитель: живёт на ноутбуке рядом с Minecraft.

Сам подключается к серверу по WebSocket (исходящее соединение, поэтому
Wi-Fi в зале и NAT не мешают), ждёт задание, выбирает свободный участок
города и строит постройку слоями, отправляя прогресс обратно.

Запуск:
    ./venv/bin/python -m builder.worker
    ./venv/bin/python -m builder.worker --reset-city   # забыть все участки
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import json
import logging
import os
import time
from pathlib import Path

import websockets
from dotenv import load_dotenv
from gdpc import interface

from .build import build, make_editor
from .placement import City
from .schema import BuildProgram

log = logging.getLogger("worker")

RECONNECT_MIN, RECONNECT_MAX = 1.0, 15.0
PROGRESS_EVERY = 0.4            # не чаще, чем раз в 0.4 с — незачем спамить


async def send(ws, payload: dict) -> None:
    await ws.send(json.dumps(payload, ensure_ascii=False))


async def handle_build(ws, message: dict, city: City, editor,
                       duration: float) -> None:
    """Одно задание: участок -> площадка -> постройка -> отчёт."""
    request_id = message["id"]
    program = BuildProgram.model_validate(message["program"])
    size = program.real_size()
    origin = city.reserve(size, program.name, request_id)
    log.info("#%s «%s» %s -> участок %s", request_id, program.name,
             list(size), origin)

    loop = asyncio.get_running_loop()
    last_sent = 0.0

    def on_layer(done: int, total: int) -> None:
        """Зовётся из рабочего потока, поэтому кладём отправку в петлю."""
        nonlocal last_sent
        now = time.time()
        if now - last_sent < PROGRESS_EVERY and done != total:
            return
        last_sent = now
        asyncio.run_coroutine_threadsafe(
            send(ws, {"type": "progress", "id": request_id,
                      "done": done, "total": total}), loop)

    # площадка и дорожка — быстро, без анимации
    await asyncio.to_thread(functools.partial(
        build, city.pad_program(origin, size), origin,
        editor=editor, delay=0.0))
    # сама постройка — слоями, на глазах
    report = await asyncio.to_thread(functools.partial(
        build, program, origin, editor=editor,
        duration=duration, clear=True, on_layer=on_layer))

    await send(ws, {"type": "done", "id": request_id,
                    "blocks": report["blocks"], "seconds": report["seconds"],
                    "origin": list(origin)})
    log.info("#%s готов: %s блоков за %s с", request_id,
             report["blocks"], report["seconds"])


async def session(url: str, city: City, editor, duration: float) -> None:
    """Одно подключение к серверу: живёт, пока сокет жив."""
    async with websockets.connect(url, ping_interval=20) as ws:
        log.info("подключился к серверу")
        await send(ws, {"type": "hello",
                        "minecraft": interface.getVersion(),
                        "city_center": list(city.center),
                        "plots_taken": len(city.taken)})
        async for raw in ws:
            message = json.loads(raw)
            if message.get("type") != "build":
                continue
            try:
                await handle_build(ws, message, city, editor, duration)
            except Exception as e:
                # упавшая постройка не должна ронять воркер и держать очередь
                log.exception("задание #%s упало", message.get("id"))
                await send(ws, {"type": "failed", "id": message.get("id"),
                                "error": f"{type(e).__name__}: {e}"})


async def run(url: str, duration: float) -> None:
    """Вечная петля с переподключением."""
    city = City()
    editor = make_editor(os.getenv("MC_HTTP", "http://localhost:9000"))
    delay = RECONNECT_MIN
    while True:
        try:
            await session(url, city, editor, duration)
            delay = RECONNECT_MIN
        except Exception as e:
            log.warning("нет связи с сервером (%s), пробую через %.0f с",
                        type(e).__name__, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX)


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    secret = os.getenv("WORKER_SECRET") or os.getenv("ADMIN_SECRET", "dev")
    default_url = f"ws://localhost:8000/ws/worker?secret={secret}"

    ap = argparse.ArgumentParser(description="Воркер-строитель")
    ap.add_argument("--url", default=os.getenv("VDS_WS_URL", default_url),
                    help="адрес WebSocket сервера")
    ap.add_argument("--duration", type=float,
                    default=float(os.getenv("BUILD_DURATION", 10)),
                    help="за сколько секунд строить одну постройку")
    ap.add_argument("--reset-city", action="store_true",
                    help="забыть занятые участки и строить с центра")
    args = ap.parse_args()

    if args.reset_city:
        City().reset()
        log.info("участки города очищены")

    url = args.url
    if "secret=" not in url:
        url = f"{url}{'&' if '?' in url else '?'}secret={secret}"

    try:
        print(f"Minecraft: {interface.getVersion()}")
    except Exception as e:
        log.error("Minecraft не отвечает на %s: %s",
                  os.getenv("MC_HTTP", "http://localhost:9000"), e)
        return

    asyncio.run(run(url, args.duration))


if __name__ == "__main__":
    main()
