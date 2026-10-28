# AI SOC Analyst

Given an incident, the analyst writes a structured investigation report. It works **with no API key** (an offline
analyst) and can use a **real language model** when you configure one. Either way you always get a report, and the
report always says who wrote it.

## What goes in

For one incident the backend assembles a context from real data: the incident (type, severity, entities, risk score and
its five-factor breakdown), its alerts, its evidence events, the correlation trail, the MITRE techniques mapped from the
rules that fired, and the extracted indicators. Nothing is invented at this stage.

## What comes out

Executive summary, what happened, timeline, **observed evidence**, **inference**, affected assets, indicators, MITRE
mapping, risk explanation, recommended investigation / containment / remediation, **unknown information**, and questions
for the analyst. Facts and interpretation are separate fields, and gaps are listed rather than papered over.

## Connect a real model (Groq, about 5 minutes)

1. Create a free account at <https://console.groq.com> and make a key under **API Keys** (it starts with `gsk_` and is
   shown once, so copy it).
2. Open `.env` in the project root (create it with `cp .env.example .env` if needed) and set:

   ```text
   AI_PROVIDER=groq
   AI_API_KEY=gsk_your_key_here
   AI_MODEL=
   ```

   Leaving `AI_MODEL` empty uses `llama-3.3-70b-versatile`. Provider catalogues change often, so if a model is rejected
   pick a current one from <https://console.groq.com/docs/models>. Prefer a larger model: small ones frequently ignore
   the required JSON format.
3. Apply it. Docker: `docker compose up -d --force-recreate backend`. Local: restart `uvicorn`.
4. **Verify the connection** (never prints your key):

   ```bash
   docker compose exec backend python scripts/check_ai.py      # locally: python scripts/check_ai.py
   ```

   It sends one synthetic incident through the same code the app uses and reports `OK`, or the exact reason it failed
   (bad key, unknown model, rate limit, no network, unusable reply) with a hint.
5. Open **System Health** or **AI SOC Analyst**: the AI card should say **live model** with the model name. Run an
   investigation: the report's `generated_by` reads `llm:groq:<model>`.

Never commit `.env` (it is git-ignored). The key stays on the server: no API response, report, audit entry or log line
contains it.

### Other providers

| `AI_PROVIDER` | Also set | Notes |
|---|---|---|
| `groq` | `AI_API_KEY` | model defaults to `llama-3.3-70b-versatile` |
| `openrouter` | `AI_API_KEY`, `AI_MODEL` | there is no default model: OpenRouter ids look like `vendor/model` |
| `openai_compatible` | `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` | any OpenAI-style endpoint, for example a local gateway such as Ollama's `/v1` (it ignores the key, but a non-empty value is required) |
| `mock` (default) | nothing | the offline analyst |

Gemini is not supported by name. The `AI_PROVIDER`/`AI_BASE_URL` combination for other providers has not been tried here.

## What leaves your machine

With a live model, the incident context (alerts, events, entities, risk breakdown) is sent to that provider. In this
project it is all synthetic, so nothing sensitive is shared; with real data you would need to consider that first.

## Safeguards for real models

A real model is less predictable than the offline analyst, so its reply is checked before anyone sees it:

| Safeguard | What it does |
|---|---|
| **Tolerant parsing** | accepts JSON inside code fences or with chatter around it, turns a lone string into a list, treats `null` as empty, ignores extra fields. A reply with no summary is rejected. |
| **MITRE table is not the model's** | techniques always come from the project's own rule-to-technique mapping, so a model cannot add or change them. |
| **Grounding guard** | any IP address or MITRE technique id that is **not in the incident data** is removed from lists or masked in prose (`[unverified]`), and the report adds a note under *Unknown information* naming what was caught. |
| **Rate-limit retry** | one retry after an HTTP 429, waiting what the provider asks for (capped at 5 seconds). |
| **Fallback** | on any other failure the offline analyst answers instead, and the report says so. |

The grounding guard checks IP addresses and technique ids, which are the things that can be verified exactly. It does
not check usernames, hostnames or counts, so the report is still advisory and an analyst should read it critically.

## Fallback labels

| `generated_by` | Meaning |
|---|---|
| `mock` | the offline analyst was configured |
| `llm:<provider>:<model>` | a real model produced the report |
| `mock (llm_failed: <ErrorType>)` | a real model was configured but failed; the offline analyst answered |

The label carries only the error *type*. The full reason (HTTP status and the provider's message, with the key masked)
is written to the server log: `docker compose logs backend`. For the usual causes see
[troubleshooting](troubleshooting.md#the-report-says-mock-llm_failed-).

## Using it

Open an incident, go to the investigation tab, and choose **Run AI investigation** (ADMIN and SOC_ANALYST; viewers can
read stored reports). The run is recorded in the audit log together with which analyst answered. Recommended containment
is advisory: it goes to the Response Center, where approval is simulated.
