"""Камера и подача: игрок телепортируется к стройке, облетает её, пока она растёт,
а на экране видно название и автор запроса.

Все команды идут с АБСОЛЮТНЫМИ координатами и по имени игрока: `runCommand` выполняется
от имени сервера в точке (0,0,0), поэтому любое `~` считалось бы от начала мира.

На время съёмки игрок переводится в режим наблюдателя (не падает, нет рук и панели,
кадр чище), а в конце возвращается в прежний режим. Любая ошибка камеры глотается:
красивый показ не должен ломать постройку.

Включено по умолчанию. Выключить: CAMERA=off в .env. Игрок: PLAYER_NAME (иначе первый в мире).
"""

from __future__ import annotations

import json
import math
import os
import re
import time

from gdpc import interface

TICK = 0.05                      # один кадр на игровой тик, 20 кадров в секунду
MODES = {0: "survival", 1: "creative", 2: "adventure", 3: "spectator"}
_POS = re.compile(r"Pos:\[([-\d.]+)d,([-\d.]+)d,([-\d.]+)d\]")
_ROT = re.compile(r"Rotation:\[([-\d.]+)f,([-\d.]+)f\]")
_MODE = re.compile(r"playerGameType:(\d)")


def clean(text: object, limit: int = 60) -> str:
    """Текст человека попадает в команду, поэтому режем управляющие символы и длину."""
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(text or "")).strip()[:limit]


def component(text: object) -> str:
    """Текстовый компонент Minecraft. json.dumps сам экранирует кавычки и слэши."""
    return json.dumps({"text": clean(text)}, ensure_ascii=False)


def shot(origin, size, angle_deg: float, closeness: float = 1.0):
    """Точка камеры на орбите и точка, на которую она смотрит."""
    ox, oy, oz = origin
    sx, sy, sz = size
    cx, cz = ox + sx / 2, oz + sz / 2
    cy = oy + max(2.0, sy * 0.45)
    radius = (max(sx, sz) * 0.9 + sy * 0.35 + 14) * closeness
    height = oy + sy * 0.65 + 8
    a = math.radians(angle_deg)
    return (cx + radius * math.cos(a), height, cz + radius * math.sin(a)), (cx, cy, cz)


class Camera:
    def __init__(self, host: str | None = None):
        self.enabled = os.getenv("CAMERA", "on").lower() not in ("off", "0", "false", "no")
        self.host = host or os.getenv("MC_HTTP", "http://localhost:9000")
        self.name = os.getenv("PLAYER_NAME") or None
        self.original_mode: str | None = None
        self.angle = -60.0
        self.pos = None          # где камера была в последний раз (для звука)
        self.rotation = None
        self.speed = max(1.0, float(os.getenv("CAMERA_SPEED", "8")))
        self.transition_seconds = max(0.5, float(os.getenv("CAMERA_TRANSITION", "3")))

    # --- низкий уровень ----------------------------------------------------

    def _run(self, command: str) -> bool:
        try:
            result = interface.runCommand(command, host=self.host, timeout=2)
            return bool(result) and all(ok for ok, _ in result)
        except Exception:
            return False

    def _find_player(self) -> bool:
        """Запоминаем имя игрока и его режим игры."""
        try:
            players = interface.getPlayers(host=self.host)
        except Exception:
            return False
        for player in players:
            if self.name and player.get("name") != self.name:
                continue
            self.name = player.get("name")
            data = player.get("data", "")
            pos = _POS.search(data)
            rot = _ROT.search(data)
            if pos:
                self.pos = tuple(float(v) for v in pos.groups())
            if rot:
                self.rotation = tuple(float(v) for v in rot.groups())
            match = _MODE.search(data)
            if match and self.original_mode is None:
                self.original_mode = MODES.get(int(match.group(1)), "creative")
            return bool(self.name)
        return False

    def quiet(self) -> None:
        """Выключить отчёты о командах в чате: иначе каждый телепорт камеры (≈10 в секунду) пишет
        строку «[GDMC-CommandHandler: Teleported …]» и чат забивает экран."""
        for rule in ("sendCommandFeedback", "logAdminCommands", "commandBlockOutput"):
            self._run(f"gamerule {rule} false")

    def _look(self, pos, target):
        dx, dy, dz = (b - a for a, b in zip(pos, target))
        yaw = math.degrees(math.atan2(-dx, dz))
        pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
        if self.rotation is not None:
            yaw = self.rotation[0] + (yaw - self.rotation[0] + 180) % 360 - 180
        return yaw, pitch

    def _pose(self, pos, rotation) -> None:
        x, y, z = pos
        yaw, pitch = rotation
        if self._run(f"tp {self.name} {x:.4f} {y:.4f} {z:.4f} {yaw:.4f} {pitch:.4f}"):
            self.pos, self.rotation = tuple(pos), tuple(rotation)

    def _tp(self, pos, target) -> None:
        self._pose(pos, self._look(pos, target))

    def _frames(self, seconds, stop=None):
        """Считаем время команды внутри кадра; после задержек не догоняем скачком."""
        elapsed = 0.0
        previous = time.monotonic()
        while stop is None or not stop.is_set():
            started = time.monotonic()
            elapsed += min(started - previous, TICK * 2)
            previous = started
            yield min(elapsed / max(seconds, TICK), 1.0)
            if elapsed >= seconds:
                return
            delay = max(0.0, TICK - (time.monotonic() - started))
            if stop is not None:
                if stop.wait(delay):
                    return
            else:
                time.sleep(delay)

    def transition(self, pos, target, stop=None) -> None:
        """Мягко меняем положение и направление между сценами."""
        if self.pos is None or self.rotation is None:
            self._tp(pos, target)
            return
        start_pos, start_rot = self.pos, self.rotation
        end_rot = self._look(pos, target)
        for t in self._frames(self.transition_seconds, stop):
            ease = t * t * (3 - 2 * t)
            self._pose(tuple(a + (b - a) * ease for a, b in zip(start_pos, pos)),
                       tuple(a + (b - a) * ease for a, b in zip(start_rot, end_rot)))

    # --- сцены -------------------------------------------------------------

    def begin(self, title: str, text: str, origin, size) -> None:
        """Перелёт к площадке и заставка с названием."""
        if not self.enabled:
            return
        try:
            if not self._find_player():
                return
            self._run(f"gamemode spectator {self.name}")
            self.angle = -60.0
            self.transition(*shot(origin, size, self.angle))
            self._run("time set day")                  # полдень и ясно: кадр всегда яркий
            self._run("weather clear")
            self._title(title, text)
        except Exception:
            pass

    def _title(self, title: str, subtitle: str) -> None:
        self._run(f"title {self.name} times 10 90 25")
        self._run(f"title {self.name} subtitle {component(subtitle)}")
        self._run(f"title {self.name} title {component(title)}")

    def actionbar(self, text: str, color: str = "gold") -> None:
        """Строка над панелью: прогресс стройки."""
        if self.enabled and self.name:
            self._run(f"title {self.name} actionbar "
                      + json.dumps({"text": clean(text), "color": color}, ensure_ascii=False))

    def idle(self, stop, stops: list) -> None:
        """Пока очередь пуста: камера по кругу облетает построенные здания (свежие первыми).
        Останавливается сразу, как только stop выставлен (пришла новая постройка)."""
        if not self.enabled or not stops:
            return
        try:
            if not self._find_player():
                return
            self._run(f"gamemode spectator {self.name}")
            i = 0
            while not stop.is_set():
                name, origin, size = stops[i % len(stops)]
                self.transition(*shot(origin, size, self.angle), stop=stop)
                if stop.is_set():
                    break
                self._title(name, "built here today")
                self.orbit(origin, size, 16.0, sweep=200.0, stop=stop)
                i += 1
        except Exception:
            pass

    def orbit(self, origin, size, seconds: float, sweep: float = 220.0,
              closeness: float = 1.0, stop=None) -> None:
        """Равномерный облёт с ограничением скорости и прерываемым ожиданием."""
        if not self.enabled or not self.name:
            return
        try:
            start = self.angle
            # Ограничиваем угловую скорость: короткая стройка не ускоряет облёт.
            sweep = math.copysign(min(abs(sweep), self.speed * seconds), sweep)
            for t in self._frames(seconds, stop):
                self.angle = start + sweep * t
                self._tp(*shot(origin, size, self.angle, closeness))
        except Exception:
            pass

    def finish(self, origin, size, hold: float = 3.0, restore: bool = True) -> None:
        """Финальный кадр с лёгким дрейфом, салют и возврат прежнего режима."""
        if not self.enabled or not self.name:
            return
        try:
            ox, oy, oz = origin
            sx, sy, sz = size
            cx, cz, top = ox + sx / 2, oz + sz / 2, oy + sy + 2
            # звук — в точке камеры: без позиции он играет у (0,0,0) и далеко от игрока не слышен
            px, py, pz = self.pos or (cx, top, cz)
            self._run(f"playsound minecraft:entity.player.levelup master {self.name} "
                      f"{px:.1f} {py:.1f} {pz:.1f} 1 1")
            self._run(f"particle minecraft:happy_villager {cx:.1f} {oy + sy / 2:.1f} {cz:.1f} "
                      f"{sx / 3:.1f} {sy / 3:.1f} {sz / 3:.1f} 0 120 force")
            for dx, dz, colors in ((-sx / 3, 0, "16711680,16776960"),
                                   (sx / 3, 0, "255,65280"),
                                   (0, sz / 3, "16711935,16777215")):
                self._run(
                    f"summon minecraft:firework_rocket {cx + dx:.1f} {top:.1f} {cz + dz:.1f} "
                    '{LifeTime:18,FireworksItem:{id:"minecraft:firework_rocket",count:1,'
                    'components:{"minecraft:fireworks":{explosions:[{shape:"large_ball",'
                    f"colors:[I;{colors}],fade_colors:[I;16777215],has_trail:1b}}],"
                    "flight_duration:1}}}}")
            self.orbit(origin, size, hold, sweep=25.0, closeness=1.0)
        except Exception:
            pass
        finally:
            if restore:
                self.restore()

    def restore(self) -> None:
        """Вернуть игроку прежний режим. Зовётся и при ошибке постройки."""
        if self.name and self.original_mode:
            self._run(f"gamemode {self.original_mode} {self.name}")
            self.original_mode = None
