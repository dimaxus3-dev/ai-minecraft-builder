"""Схема программы постройки.

Это контракт между LLM и строителем. LLM выдаёт JSON такого вида:

    {
      "name": "Маяк",
      "size": [11, 24, 11],
      "parts": [
        {"type": "cylinder", "center": [5, 0, 5], "radius": 5,
         "height": 18, "hollow": true, "block": "white_concrete"},
        {"type": "sphere", "center": [5, 20, 5], "radius": 3,
         "block": "glowstone"}
      ]
    }

Координаты — относительно точки постройки: x вправо, y вверх, z вперёд.
Геометрию LLM не считает: только примитивы, остальное делает наш код.
"""

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .blocks import normalize

# Пределы. SIZE_LIMIT по умолчанию 40 (как договорились), для мостов
# и прочих длинных штук вызывающий код передаёт свой лимит.
DEFAULT_SIZE_LIMIT = 40
MAX_COORD = 256          # жёсткий предел на любую координату
MAX_PARTS = 250          # больше LLM всё равно осмысленно не выдаёт
MAX_BLOCKS = 400_000     # защита от «сплошной куб 200x200x200»

Vec3 = tuple[int, int, int]


class _Part(BaseModel):
    """Общее для всех примитивов: материал."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    block: str = "stone"

    @field_validator("block", mode="before")
    @classmethod
    def _clean_block(cls, v: object) -> str:
        # неизвестные и выдуманные id превращаются в stone
        return normalize(v if isinstance(v, str) else None)


class Box(_Part):
    """Сплошной параллелепипед между двумя углами."""

    type: Literal["box"]
    start: Vec3 = Field(alias="from")
    end: Vec3 = Field(alias="to")


class HollowBox(_Part):
    """Коробка со стенками: пол, потолок и четыре стены."""

    type: Literal["hollow_box"]
    start: Vec3 = Field(alias="from")
    end: Vec3 = Field(alias="to")
    thickness: int = Field(default=1, ge=1, le=8)


class Cylinder(_Part):
    """Цилиндр или труба; center — центр основания."""

    type: Literal["cylinder"]
    center: Vec3
    radius: int = Field(ge=0, le=64)
    height: int = Field(ge=1, le=128)
    hollow: bool = False
    axis: Literal["x", "y", "z"] = "y"


class Sphere(_Part):
    """Шар или сфера-скорлупа."""

    type: Literal["sphere"]
    center: Vec3
    radius: int = Field(ge=0, le=48)
    hollow: bool = False


class Line(_Part):
    """Линия между двумя точками, с толщиной."""

    type: Literal["line"]
    start: Vec3 = Field(alias="from")
    end: Vec3 = Field(alias="to")
    thickness: int = Field(default=1, ge=1, le=8)


class Roof(_Part):
    """Крыша над прямоугольником start..end; высота y берётся из start."""

    type: Literal["roof"]
    start: Vec3 = Field(alias="from")
    end: Vec3 = Field(alias="to")
    style: Literal["gable", "pyramid", "flat"] = "gable"
    height: Optional[int] = Field(default=None, ge=1, le=64)
    axis: Optional[Literal["x", "z"]] = None


class Arch(_Part):
    """Арка: полуэллипс от одного основания до другого."""

    type: Literal["arch"]
    start: Vec3 = Field(alias="from")
    end: Vec3 = Field(alias="to")
    height: int = Field(ge=1, le=128)
    thickness: int = Field(default=1, ge=1, le=8)


AnyPart = Annotated[
    Union[Box, HollowBox, Cylinder, Sphere, Line, Roof, Arch],
    Field(discriminator="type"),
]


class BuildProgram(BaseModel):
    """Программа постройки целиком."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(min_length=1, max_length=80)
    size: Vec3
    parts: list[AnyPart] = Field(min_length=1, max_length=MAX_PARTS)

    @field_validator("size")
    @classmethod
    def _check_size(cls, v: Vec3) -> Vec3:
        if any(a < 1 for a in v):
            raise ValueError("size: все три измерения должны быть >= 1")
        if any(a > MAX_COORD for a in v):
            raise ValueError(f"size: измерение больше {MAX_COORD} блоков")
        return v

    @model_validator(mode="after")
    def _check_coords(self) -> "BuildProgram":
        """Никакая точка не должна улетать за MAX_COORD от точки постройки."""
        for i, part in enumerate(self.parts):
            for name in ("start", "end", "center"):
                point = getattr(part, name, None)
                if point and any(abs(a) > MAX_COORD for a in point):
                    raise ValueError(
                        f"parts[{i}].{name}: координата больше {MAX_COORD}"
                    )
        return self

    def real_size(self) -> Vec3:
        """Настоящие габариты по частям.

        LLM часто объявляет `size` наугад, поэтому доверять ему нельзя:
        считаем по фактической геометрии.
        """
        from .primitives import cells_of

        xs: list[int] = []
        ys: list[int] = []
        zs: list[int] = []
        for part in self.parts:
            for x, y, z in cells_of(part):
                xs.append(x)
                ys.append(y)
                zs.append(z)
        if not xs:
            return (0, 0, 0)
        return (max(xs) - min(xs) + 1,
                max(ys) - min(ys) + 1,
                max(zs) - min(zs) + 1)

    def fits(self, limit: int) -> bool:
        """Влезает ли постройка в куб limit x limit x limit (по факту)."""
        return all(a <= limit for a in self.real_size())


def schema_for_prompt() -> str:
    """Короткое описание примитивов для системного промпта LLM (Фаза 2)."""
    return """\
box:         {"type":"box","from":[x,y,z],"to":[x,y,z],"block":"..."}
hollow_box:  {"type":"hollow_box","from":[x,y,z],"to":[x,y,z],"thickness":1,"block":"..."}
cylinder:    {"type":"cylinder","center":[x,y,z],"radius":r,"height":h,"hollow":false,"axis":"y","block":"..."}
sphere:      {"type":"sphere","center":[x,y,z],"radius":r,"hollow":false,"block":"..."}
line:        {"type":"line","from":[x,y,z],"to":[x,y,z],"thickness":1,"block":"..."}
roof:        {"type":"roof","from":[x,y,z],"to":[x,y,z],"style":"gable|pyramid|flat","height":h,"block":"..."}
arch:        {"type":"arch","from":[x,y,z],"to":[x,y,z],"height":h,"thickness":1,"block":"..."}

y=0 — уровень земли, y растёт вверх. Части рисуются по порядку:
следующая часть перекрывает предыдущую (так делают окна и двери — блоком "air").\
"""
