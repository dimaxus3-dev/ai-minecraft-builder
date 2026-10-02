"""Воркер-строитель: живёт на ноутбуке рядом с Minecraft.

Сам подключается к серверу по WebSocket (исходящее соединение, поэтому Wi-Fi в зале и NAT не мешают),
ждёт задание, выбирает свободный участок города и строит постройку слоями, отправляя прогресс обратно.
Пока строит, камера облетает здание; когда очередь пуста, камера возит по уже построенным.

Запуск:
    ./venv/bin/python -m builder.worker
    ./venv/bin/python -m builder.worker --reset-city   # забыть все участки и список построенного
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import functools
import json
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

import websockets
from dotenv import load_dotenv
from gdpc import interface

from .build import build, make_editor
from .camera import Camera
from .placement import City
from .schema import BuildProgram

log = logging.getLogger("worker")

RECONNECT_MIN, RECONNECT_MAX = 1.0, 15.0
PROGRESS_EVERY = 0.4            # не чаще, чем раз в 0.4 с — незачем спамить
BUILT_FILE = Path(os.getenv("BUILT_FILE", "data/built.json"))
SOURCE_LABELS = {"blueprint": "готовый чертёж", "osm": "реальные данные карты OpenStreetMap",
                 "model": "придумал ИИ"}

_SHOW: "Show | None" = None


class Show:
    """Режиссёр показа: одна камера на всё время работы и «экскурсия» по готовым зданиям,
    пока очередь пуста. Список построенного лежит в файле и переживает перезапуск."""

    def __init__(self) -> None:
        self.cam = Camera()
        self.cam.quiet()                      # чат без отчётов о каждом телепорте
        self.idle_on = os.getenv("CAMERA_IDLE", "on").lower() not in ("off", "0", "false", "no")
        self.built: list[dict] = self._load()
        self._stop: threading.Event | None = None
        self._task: asyncio.Task | None = None

    def _load(self) -> list[dict]:
        try:
            return json.loads(BUILT_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []

    def reset(self) -> None:
        self.built = []
        BUILT_FILE.parent.mkdir(parents=True, exist_ok=True)
        BUILT_FILE.write_text("[]", encoding="utf-8")

    def add(self, name: str, origin, size) -> None:
        self.built = [b for b in self.built if b["origin"] != list(origin)]
        self.built.append({"name": name, "origin": list(origin), "size": list(size)})
        self.built = self.built[-12:]
        BUILT_FILE.parent.mkdir(parents=True, exist_ok=True)
        BUILT_FILE.write_text(json.dumps(self.built, ensure_ascii=False), encoding="utf-8")

    def stops(self) -> list:
        return [(b["name"], tuple(b["origin"]), tuple(b["size"])) for b in reversed(self.built)]

    def start_idle(self) -> None:
        """Пустая очередь: камера кружит по зданиям (если выключено — игрок получает управление)."""
        if not (self.idle_on and self.cam.enabled and self.built):
            return
        self._stop = threading.Event()
        self._task = asyncio.create_task(asyncio.to_thread(self.cam.idle, self._stop, self.stops()))

    async def stop_idle(self) -> None:
        if self._stop is not None:
            self._stop.set()
            if self._task is not None:
                await self._task
        self._stop = self._task = None


async def send(ws, payload: dict) -> None:
    await ws.send(json.dumps(payload, ensure_ascii=False))


async def handle_build(ws, message: dict, city: City, editor, duration: float, show: Show) -> None:
    """Одно задание: участок -> площадка -> постройка с облётом -> отчёт -> салют."""
    await show.stop_idle()
    cam = show.cam
    request_id = message["id"]
    program = BuildProgram.model_validate(message["program"])
    size = program.real_size()
    origin = city.reserve(size, program.name, request_id)
    log.info("#%s «%s» %s [%s] -> участок %s", request_id, program.name, list(size),
             program.source or "?", origin)

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
            send(ws, {"type": "progress", "id": request_id, "done": done, "total": total}), loop)
        cam.actionbar(f"Строится… {round(100 * done / total)}%")

    label = SOURCE_LABELS.get(program.source, "")
    if program.source == "model" and program.model:
        label = f"придумал ИИ: {program.model.split('/')[-1]}"
    await asyncio.to_thread(cam.begin, program.name, label or message.get("text", ""), origin, size)
    try:
        # площадка и дорожка — быстро, без анимации
        await asyncio.to_thread(functools.partial(
            build, city.pad_program(origin, size), origin, editor=editor, delay=0.0))
        # сама постройка растёт слоями, а камера в это время облетает её
        flight = asyncio.create_task(asyncio.to_thread(cam.orbit, origin, size, duration))
        report = await asyncio.to_thread(functools.partial(
            build, program, origin, editor=editor,
            duration=duration, clear=True, on_layer=on_layer))
        await flight
    except Exception:
        cam.restore()           # игрок не должен остаться в режиме наблюдателя
        raise

    await send(ws, {"type": "done", "id": request_id,
                    "blocks": report["blocks"], "seconds": report["seconds"],
                    "origin": list(origin)})
    log.info("#%s готов: %s блоков за %s с", request_id, report["blocks"], report["seconds"])
    show.add(program.name, origin, size)
    # салют и финальный кадр: статус «готово» уже ушёл, очередь не ждёт
    await asyncio.to_thread(cam.finish, origin, size, 3.0, not show.idle_on)
    show.start_idle()                                    # дальше камера кружит, пока нет новых заданий


async def session(url: str, city: City, editor, duration: float, show: Show) -> None:
    """Одно подключение к серверу: живёт, пока сокет жив."""
    async with websockets.connect(url, ping_interval=20, max_size=None) as ws:
        log.info("подключился к серверу")
        await send(ws, {"type": "hello", "minecraft": interface.getVersion(),
                        "city_center": list(city.center), "plots_taken": len(city.taken)})
        show.start_idle()                                # очередь пуста: показываем уже построенное
        try:
            async for raw in ws:
                message = json.loads(raw)
                if message.get("type") != "build":
                    continue
                try:
                    await handle_build(ws, message, city, editor, duration, show)
                except Exception as e:
                    # упавшая постройка не должна ронять воркер и держать очередь
                    log.exception("задание #%s упало", message.get("id"))
                    await send(ws, {"type": "failed", "id": message.get("id"),
                                    "error": f"{type(e).__name__}: {e}"})
        finally:
            await show.stop_idle()


async def run(url: str, duration: float) -> None:
    """Вечная петля с переподключением."""
    global _SHOW
    city = City()
    editor = make_editor(os.getenv("MC_HTTP", "http://localhost:9000"))
    show = _SHOW = Show()
    delay = RECONNECT_MIN
    while True:
        try:
            await session(url, city, editor, duration, show)
            delay = RECONNECT_MIN
        except Exception as e:
            log.warning("нет связи с сервером (%s), пробую через %.0f с", type(e).__name__, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX)


def _bye(*_args) -> None:
    """Остановка воркера: вернуть игроку обычный режим, а не оставлять наблюдателем."""
    if _SHOW is not None:
        _SHOW.cam.restore()
    sys.exit(0)


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    secret = os.getenv("WORKER_SECRET") or os.getenv("ADMIN_SECRET", "dev")
    default_url = f"ws://localhost:8000/ws/worker?secret={secret}"

    ap = argparse.ArgumentParser(description="Воркер-строитель")
    ap.add_argument("--url", default=os.getenv("VDS_WS_URL", default_url), help="адрес WebSocket сервера")
    ap.add_argument("--duration", type=float, default=float(os.getenv("BUILD_DURATION", 10)),
                    help="за сколько секунд строить одну постройку")
    ap.add_argument("--reset-city", action="store_true",
                    help="забыть занятые участки и список построенного, строить с центра")
    args = ap.parse_args()

    if args.reset_city:
        City().reset()
        Show().reset()
        log.info("участки города и список построенного очищены")

    url = args.url
    if "secret=" not in url:
        url = f"{url}{'&' if '?' in url else '?'}secret={secret}"

    try:
        print(f"Minecraft: {interface.getVersion()}")
    except Exception as e:
        log.error("Minecraft не отвечает на %s: %s", os.getenv("MC_HTTP", "http://localhost:9000"), e)
        return

    signal.signal(signal.SIGTERM, _bye)
    signal.signal(signal.SIGINT, _bye)
    atexit.register(lambda: _SHOW and _SHOW.cam.restore())
    asyncio.run(run(url, args.duration))


if __name__ == "__main__":
    main()
