# AI Minecraft Builder

Type what you want built — *"a lighthouse"*, *"a dragon"*, *"a bridge with a wheelchair ramp"* — in any language.
An **open-weight LLM** designs it, a human moderator approves it, and it grows layer by layer in a shared
Minecraft city next to everyone else's ideas.

Built for the SF Hacks × GDG AI Hackathon (Oct 2, 2026), **MLH track: Best Open-Source AI Project**.

## How it works

```
phone (QR → web page) → FastAPI server → SQLite queue → moderator approves in /admin
   → open-weight LLM writes a JSON "build program" → pydantic validates it
   → WebSocket → worker on the laptop → gdpc → Minecraft (built bottom-up, layer by layer)
```

The model never writes a list of blocks. It writes a short **program** made of seven geometric
primitives (`box`, `hollow_box`, `cylinder`, `sphere`, `line`, `roof`, `arch`) using a whitelist of
~250 block ids that exist in Minecraft 1.21.4. Our own code computes the geometry, so the result is
deterministic, an invalid program is rejected (with one repair retry), and an unknown block becomes
`stone` instead of breaking the build. `builder/placement.py` hands out non-overlapping plots on a
spiral grid around the city centre.

## Open-weight models

Open-weight AI is the core of the project: without it a sentence cannot become a structure.

| Role | Model | License | Weights |
|---|---|---|---|
| Primary | NVIDIA Nemotron 3 Super 120B-A12B (`nvidia/nemotron-3-super-120b-a12b`) | [NVIDIA Nemotron Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/) | [Hugging Face](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16) |
| Fallback | OpenAI gpt-oss-20b (`openai/gpt-oss-20b`) | Apache 2.0 | [Hugging Face](https://huggingface.co/openai/gpt-oss-20b) |

Both are called through NVIDIA's hosted OpenAI-compatible API (`integrate.api.nvidia.com`). The client in
`backend/ai.py` only needs `LLM_BASE_URL` and `LLM_MODEL`, so it is meant to work with any
OpenAI-compatible server that hosts open weights (vLLM, Ollama, ...). **We have not tested a local
server.** If the primary model errors or times out, the fallback is tried automatically. While building
this we also benchmarked other models on the same task; availability on the hosted API varied during the
day (one model stopped responding mid-event), which is why the fallback chain exists.

## Run it

You need Minecraft Java **1.21.4** with Fabric, Fabric API `0.119.4+1.21.4` and the
[GDMC HTTP Interface](https://github.com/Niels-NTG/gdmc_http_interface) mod `1.6.0-1.21.4`
(it opens an HTTP API on `localhost:9000` when you enter a world). A Superflat creative world works best.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt -r builder/requirements.txt
cp .env.example .env            # add NVIDIA_API_KEY and set ADMIN_SECRET

python -m uvicorn backend.main:app --port 8000   # server: /, /screen, /admin-<ADMIN_SECRET>
python -m builder.worker                          # worker, on the machine running Minecraft
```

Try pieces on their own:

```bash
python -m builder.build programs/showcase.json --dry-run --origin 0 0 0   # geometry only, no game
python -m backend.ai "a lighthouse" --build                                # text -> program -> built
```

## Safety and privacy

- Nothing is built without a human approving it in the moderation page.
- One request per minute per client, a block whitelist and schema validation: the model can only emit
  the seven primitives, never an arbitrary command.
- Names are optional and there are no accounts. IP addresses are stored only as a salted hash (used for the
  rate limit) and are never returned by the API or WebSockets.

## Known limits

- Quality varies: simple buildings come out well, long structures like bridges are crude.
- Voice input is not implemented yet.
- Multilingual prompts (English, Spanish, Chinese, Tagalog, Vietnamese) produced valid programs in a quick
  test; we have not checked how recognisable each result is, and one Tagalog request took over two minutes.

## AI assistance and what was done before the event

Most of the code was written with **Claude Code** (Anthropic), an AI coding assistant, directed and reviewed
by the team. A large part of it was written **before the official hacking start (11:00, Oct 2, 2026)**:

- Before the event: Minecraft + Fabric + GDMC mod setup, early `gdpc` experiments (`test*.py`), the
  hand-made animated bridge script `bridge.py`, and — written on Oct 1 and the morning of Oct 2 up to
  the start — the builder (`builder/`), LLM generation (`backend/ai.py`), the queue/server/worker
  (`backend/`, `builder/worker.py`) and the moderation page. That state is tagged **`pre-hackathon`**. The commit itself was made at about 11:07, a few minutes
  after the start, because the repository was only created then. Every code file in it was last modified
  at 10:48 or earlier on Oct 2 (check the file modification times); only this README paragraph was
  edited at commit time.
- During the event: everything committed after that tag.

`git log` shows exactly which is which.

## License

Code: [MIT](LICENSE). The models above are under their own licenses, linked in the table.
