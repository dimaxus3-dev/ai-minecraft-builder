# AI Minecraft Builder

Хакатон SF Hacks × GDG, трек MLH «Best Open-Source AI Project», сдача на ShipYard в 16:45 (2 окт 2026).
Человек пишет, что построить → модератор одобряет → открытая LLM делает JSON-программу из примитивов →
воркер строит её в Minecraft слоями. Подробности: README.md.

## Кто за что отвечает
- `backend/`, `builder/`, `programs/` — Дима и его Claude (сервер, очередь, LLM, строитель).
- `static/` — Ethan и его Claude (страницы для людей и для экрана зала). **Задание: `static/CLAUDE.md`.**
- Чужую папку без договорённости не правим: так мы не получим конфликтов в git.

## Правила
- Репозиторий **публичный**. Секреты живут только в `.env` (он в `.gitignore`). Никогда не коммить ключи.
- Перед пушем: `git pull --rebase`. Коммиты небольшие, с понятным сообщением.
- Комментарии в коде по-русски, код простой и читаемый. Настройки только через `.env`.
- Тег `pre-hackathon` отмечает состояние до старта хакинга, его не двигаем.

## Команды
- Сервер: `python -m uvicorn backend.main:app --port 8000`
- Воркер (на ноутбуке с Minecraft): `python -m builder.worker`
- Геометрия без игры: `python -m builder.build programs/showcase.json --dry-run --origin 0 0 0`
