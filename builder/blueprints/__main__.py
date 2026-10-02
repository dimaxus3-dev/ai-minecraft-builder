"""Предпросмотр чертежа по названию:  python -m builder.blueprints eiffel_tower -o /tmp/eiffel.png"""

from __future__ import annotations

import argparse

from . import REGISTRY, build, match
from ..preview import preview


def main() -> None:
    ap = argparse.ArgumentParser(description="PNG-предпросмотр готового чертежа")
    ap.add_argument("id", help="id чертежа или название здания; без аргументов — список")
    ap.add_argument("-o", "--out", default="preview.png")
    args = ap.parse_args()
    bid = args.id if args.id in REGISTRY else match(args.id)
    if bid is None:
        print("нет такого чертежа. Есть:", ", ".join(REGISTRY))
        return
    v = build(bid)
    live = {p: b for p, b in v.items() if b != "air"}
    dims = [max(p[i] for p in live) + 1 for i in range(3)]
    print(f"{bid}: {len(live)} блоков, габариты {dims[0]}x{dims[1]}x{dims[2]}, материалов {len(set(live.values()))}")
    print("картинка:", preview(live, args.out))


if __name__ == "__main__":
    main()
