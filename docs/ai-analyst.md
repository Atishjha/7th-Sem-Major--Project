# AI SOC Analyst

Given an incident, the analyst writes a structured investigation report. It is designed so the system is
fully usable **without any API key** and never fails to produce a report.

## What goes in

For one incident, the backend assembles a context from real data: the incident (type, severity, entities,
risk score and its five-factor breakdown), its alerts, its evidence events, the correlation trail, the MITRE
techniques mapped from the rules that fired, and the extracted indicators. Nothing is invented at this stage.

## What comes out

A report with these sections: executive summary, what happened, timeline, **observed evidence**, **inference**,
affected assets, indicators, MITRE mapping, risk explanation, recommended investigation / containment /
remediation, **unknown information**, and questions for the analyst.

The key design rule is that *facts and interpretation are separate fields*: what the data shows is never mixed
with what the analyst concludes, and gaps are listed rather than papered over.

## Providers

| `AI_PROVIDER` | Behaviour |
|---|---|
| `mock` (default) | deterministic, offline, built from the incident's real values; no key needed |
| `groq`, `openrouter` | OpenAI-style chat completions with a built-in base URL |
| `openai_compatible` | any OpenAI-style endpoint; set `AI_BASE_URL` (for example a local gateway) |

Set `AI_PROVIDER`, `AI_API_KEY` and `AI_MODEL` in `.env`. The request asks for JSON output, and the reply is validated
against the report schema before it is used.

## Fallback (the important part)

If the configured provider has no key, is unreachable, times out, returns an HTTP error, returns non-JSON, or
returns JSON with the wrong shape, the **mock analyst answers instead**, and the report's `generated_by` field says so:

| `generated_by` | Meaning |
|---|---|
| `mock` | the mock analyst was configured |
| `llm:<provider>:<model>` | a real model produced the report |
| `mock (llm_failed: <ErrorType>)` | a real model was configured but failed; the mock answered |

The label never hides a fallback. Each of those failure modes is covered by an automated test.

## Using it

Open an incident, go to the investigation tab, and choose **Run AI investigation** (ADMIN and SOC_ANALYST;
viewers can read stored reports). The run is recorded in the audit log. Recommended containment is *advisory*:
it is handled in the Response Center, where approval is simulated.
