# AI Minecraft Builder

Type what you want built — *"a lighthouse"*, *"a dragon"*, *"a bridge with a wheelchair ramp"* — in any language.
An **open-weight LLM** designs it, a human moderator approves it, and it grows layer by layer in a shared
Minecraft city next to everyone else's ideas.

Built for the SF Hacks × GDG AI Hackathon (Oct 2, 2026), **MLH track: Best Open-Source AI Project**.

## How it works

```
 phone (QR -> web page) --+                              +--> big screen (/screen)
                          v                              |
                   FastAPI server --- SQLite queue --- moderator (/admin) approves
                          |  starts resolving the moment a request arrives
                          v
                   RESOLVER  (the first layer that answers wins)
                     1. blueprint  hand-built, 18 famous buildings      instant
                     2. map        OpenStreetMap outline and heights    2-4 s
                     3. model      open-weight LLM + Wikipedia facts    60-90 s
                          |  build program (JSON, with its source)
                          v  WebSocket
                   WORKER (laptop) --- gdpc ---> Minecraft, built layer by layer
                          +-- camera director: flies around the build, shows title and source,
                              fireworks at the end, tours the finished city while the queue is empty
```

The model never writes a list of blocks. It writes a short **program** made of seven geometric
primitives (`box`, `hollow_box`, `cylinder`, `sphere`, `line`, `roof`, `arch`) using a whitelist of
~250 block ids that exist in Minecraft 1.21.4. Our own code computes the geometry, so the result is
deterministic, an invalid program is rejected (with one repair retry), and an unknown block becomes
`stone` instead of breaking the build. `builder/placement.py` hands out non-overlapping plots on a
spiral grid around the city centre.

**Hand-built blueprints.** Our first version let the model design everything from primitives, and the
results were poor: its "Eiffel Tower" came out as four straight grey pillars. So for 13 well-known
buildings we ship blueprints written in code (`builder/blueprints/`): Eiffel Tower, Golden Gate Bridge,
Transamerica Pyramid, Taj Mahal, Colosseum, Great Pyramid, castle, house, skyscraper, cathedral, pagoda,
windmill and lighthouse. Each was checked by rendering it to an image (`python -m builder.preview`). A
request that names one of them is matched by name and **skips the model**, so it is instant and always
good. Everything else is designed by the open-weight model, which is also shown the blueprint list, may use one
as a base ("a castle with a dragon") and gets a short Wikipedia summary of the named landmark so it knows what it
looks like (`backend/research.py`). A named building that has no blueprint is also looked up on **OpenStreetMap** (`builder/osm.py`):
Nominatim finds it, Overpass returns its real outline, heights, roof shapes and colours, and we voxelize
them. This gives true proportions for buildings the model cannot draw (Notre-Dame, Sagrada Familia, the
Odesa opera house), but it is only massing and it is only used when the building is mapped in 3D (at least
3 `building:part` objects); otherwise the result is a lone box or a fragment, so the model is used instead.
Results are cached on disk (`data/osm_cache/`). Requests with no blueprint are logged to
`data/unmatched.txt` to show which ones to add next. Freeform results from the model alone are still much weaker
than the blueprints.

While a build grows, the worker teleports the player to it, puts them in spectator mode, flies a camera
around the structure, shows its name, where it came from (blueprint, map or model) and the progress, and ends
with fireworks. When the queue is empty the camera keeps touring the buildings already built
(`builder/camera.py`; `CAMERA=off` disables it, `CAMERA_IDLE=off` stops only the tour). The request is also generated in the background while it waits for the
moderator, so approving it starts the build within a second.

## Open-weight models

Open-weight AI is the core of the project: without it a sentence cannot become a structure.

| Priority | Model | License | Weights |
|---|---|---|---|
| 1 (best quality) | NVIDIA Nemotron 3 Ultra 550B-A55B (`nvidia/nemotron-3-ultra-550b-a55b`) | [OpenMDW-1.1](https://raw.githubusercontent.com/OpenMDW/OpenMDW/refs/heads/main/1.1/LICENSE.OpenMDW-1.1) | [Hugging Face](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16) |
| 2 | NVIDIA Nemotron 3 Super 120B-A12B (`nvidia/nemotron-3-super-120b-a12b`) | [NVIDIA Nemotron Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/) | [Hugging Face](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16) |
| 3 | OpenAI gpt-oss-20b (`openai/gpt-oss-20b`) | Apache 2.0 | [Hugging Face](https://huggingface.co/openai/gpt-oss-20b) |

All three are called through NVIDIA's hosted OpenAI-compatible API (`integrate.api.nvidia.com`). The client in
`backend/ai.py` only needs `LLM_BASE_URL` and `LLM_MODEL`, so it is meant to work with any
OpenAI-compatible server that hosts open weights (vLLM, Ollama, ...). **We have not tested a local
server.**

The hosted API changed state from minute to minute during the event (in one test both larger models timed
out while gpt-oss answered in 20 s), so the models are **raced with a delay** instead of tried in turn: the
first starts immediately, the next one starts 20 s later if there is still no answer, and the first valid
answer wins (`LLM_HEDGE_SECONDS`). A sequential chain took about 200 s in that test; the race took about 90 s.
We benchmarked other open models on the same task too; most timed out or were not available on our key.

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

- The hosted model API is the weakest link: latency ranged from 15 s to over 2 minutes and models dropped
  out during the day.
- The public Overpass mirrors are flaky; we query several in parallel and cache results, but a cold lookup can still fail and fall back to the model.
- Only the 18 hand-built blueprints look good; buildings designed by the model alone are crude.
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
