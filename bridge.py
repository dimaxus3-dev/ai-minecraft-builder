import time
from gdpc import Editor

ed = Editor()
OR = "orange_concrete"
DECK, TOP, D = 8, 36, 45
SPEED = 1.0
AT = "execute at @e[tag=bridge_origin,limit=1] run "

ed.runCommand("kill @e[type=marker,tag=bridge_origin]")
ed.runCommand('execute at @p run summon marker ~ ~ ~ {Tags:["bridge_origin"]}')
time.sleep(0.5)

def fill(x1, y1, z1, x2, y2, z2, b):
    ed.runCommand(f"{AT}fill ~{x1} ~{y1} ~{D+z1} ~{x2} ~{y2} ~{D+z2} {b}")

def col(x, z, ya, yb, b):
    fill(x, min(ya, yb), z, x, max(ya, yb), z, b)

def cable_y(x):
    return DECK + 4 + (TOP - (DECK + 4)) * (x / 22) ** 2

def pause(t):
    time.sleep(t * SPEED)

def deck(xa, xb):
    fill(xa, DECK, -6, xb, DECK, 6, "gray_concrete")
    fill(xa, DECK, 0, xb, DECK, 0, "yellow_concrete")
    fill(xa, DECK + 1, -6, xb, DECK + 1, -6, OR)
    fill(xa, DECK + 1, 6, xb, DECK + 1, 6, OR)

t0 = time.time()

fill(-40, -3, -14, 40, -1, 14, "water")

for k in range(14):
    xa, xb = k * 4, min(k * 4 + 3, 52)
    deck(xa, xb)
    deck(-xb, -xa)
    pause(0.05)

for y in range(-3, TOP + 1, 3):
    top = min(y + 2, TOP)
    for tx in (-22, 22):
        for z in (-6, 6):
            fill(tx, y, z, tx + 1, top, z, OR)
        for lvl in (14, 22, 30):
            if y <= lvl <= top:
                fill(tx, lvl, -6, tx + 1, lvl, 6, OR)
        if top >= TOP - 1:
            fill(tx, TOP - 1, -6, tx + 1, TOP, 6, OR)
    pause(0.07)

for i in range(31):
    if i <= 22:
        for x in (-22 + i, 22 - i):
            nxt = x + 1 if x < 0 else x - 1
            for z in (-6, 6):
                col(x, z, round(cable_y(x)), round(cable_y(nxt)), OR)
    for sx in (-1, 1):
        x = sx * (22 + i)
        y1 = round(TOP + (DECK + 1 - TOP) * i / 30)
        y2 = round(TOP + (DECK + 1 - TOP) * (i + 1) / 30)
        for z in (-6, 6):
            col(x, z, y1, y2, OR)
    pause(0.04)

for x in sorted(range(-21, 22, 3), key=abs):
    for z in (-6, 6):
        col(x, z, DECK + 1, round(cable_y(x)) - 1, OR)
    pause(0.08)

print("Готово за", round(time.time() - t0, 1), "сек")
