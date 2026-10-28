# Demo script (about 10 minutes)

A walkthrough that shows every capability in a sensible order, with what to say and what to point at.
Everything below uses real labels from the app. Start from a clean state with `docker compose up --build`
(see the README), then open <http://localhost:5173>.

> **Say this first (20 seconds):** "This is a simplified SOC. All events are simulated and every response action is
> simulated; nothing touches a real system. I'll attack it, show how it detects and explains the attack, and show what
> an analyst can and can't do."

## 0. Before you start

* Sign in as **analyst / analyst123**. Keep a second browser profile ready for **viewer / viewer123**.
* **Seed baseline data once** so the ML step has enough to train on (the scenarios alone come from a single IP and
  produce too few time windows; training needs at least 5):
  `docker compose exec backend python scripts/seed_demo_data.py`  (or `python scripts/seed_demo_data.py` from the project root when running locally).
  It adds 600 synthetic baseline events and is safe to re-run (it skips if events already exist).
* If the database already has incidents from earlier, that is fine; the new one will simply be the newest.

## 1. Run an attack (1 min): *Demo Mode*

Choose **Multi-stage incident** and start it. The scenario plays out over about 10 seconds (10 events).
Point out that the events stream live; this is the WebSocket feed.

*Say:* "A brute-force login, a login from an impossible location, a hidden PowerShell command, then a large outbound
transfer: four stages of one attack."

## 2. Dashboard (1 min): *Dashboard*

Show the KPIs, the live event feed, and the charts (events over time, severity, detection type).
*Say:* "These numbers are computed from real rows. On an empty system the detection-rate card shows no figure rather
than inventing one."

## 3. Detection (1 min): *Alerts* and *Detection Engine*

Open **Alerts**: four alerts, one per rule. Open **Detection Engine** and show the rule settings.
**Live change:** raise the brute-force threshold, re-run the *Brute force* scenario and show it no longer fires;
set it back. *Say:* "Rules are data, not code. The change took effect immediately and is in the audit log."

## 4. The incident (2 min): *Incidents* then the incident

All four alerts were grouped into **one incident**. Open it and walk the tabs:

* **Overview:** the risk score and its **five-factor breakdown**; "every point is explained".
  Also the **correlation trail**: for each alert, *why* it joined the incident.
* **Timeline / Evidence:** the raw events behind each alert.
* **Entities:** users, IPs, hosts, destinations involved.
* **MITRE ATT&CK:** techniques T1110, T1078, T1059.001 and T1041 mapped from the rules that fired.

## 5. AI investigation (1-2 min): *AI Investigation* tab

Click **Run AI investigation**. Point out that the report separates **observed evidence** from **inference** and lists
**unknown information**, and read the `generated_by` label.

* **With a real model configured** (see [ai-analyst.md](ai-analyst.md)): first show **System Health** or **AI SOC Analyst**,
  where the AI card says **live model** and the model name. The report is labelled `llm:groq:<model>`.
  *Say:* "This is a real language model, but I don't trust it blindly. Its MITRE table comes from my own rule mapping, and
  a grounding check removes any IP address or technique it invents that isn't in the incident data."
* **Without a key:** it works offline. *Say:* "By default an offline analyst answers, so the demo needs no internet."
* **Safety net:** if the model is unreachable the label reads `mock (llm_failed: ...)` and the demo carries on. *Say:*
  "It never silently pretends: the report says which analyst wrote it."

## 6. Response (1 min): *Response* tab, then *Response Center*

Three recommended actions for the account. **Approve** one and **Reject** another. Show the result text:
"...would be disabled. No real account was modified."
*Say:* "Approval is simulated by design, and an action can only be decided once."

## 7. ML (1 min): *ML Anomaly Detection*

Train the model **after** the attack. Show the model status and the top anomalous windows: the attacker's window is
usually at or near the top (5 failed logins, process executions and a large outbound transfer in one 5-minute window; the
transfer size is randomised, so a small one ranks lower). Point at the line
saying accuracy is **not applicable** because there are no labels. *Say:* "I only report accuracy when real labels exist."

Then re-open the incident (Overview): training re-scored it, so the **ML anomaly** factor in the risk breakdown now has
points and the total has risen. *Say:* "The score isn't frozen at creation; when the model learns something new,
existing incidents are re-scored, and that is audited too."
If the factor is still 0, the attacker's window wasn't among the flagged ones (the model flags the top `contamination`
fraction, 5% by default): train again with contamination 0.1.

## 8. Real dataset (1 min): *Dataset & ML*

Upload `nslkdd_binary.csv` (see [ml-and-datasets.md](ml-and-datasets.md)), preprocess with label column `label`, train with
attack value `attack`. Now the page shows real accuracy, precision, recall and a confusion matrix.
*Say:* "Isolation Forest is unsupervised, so recall on a clustered attack class is moderate; I'd rather show an honest
number than a flattering one."

## 9. Accountability and roles (1 min): *Audit Logs*, then the viewer

Open **Audit Logs**: every action so far (rule change, investigation, approve/reject, ML training) with who and when.
Then switch to the **viewer** profile: everything is visible, but there are no Approve/Reject buttons and the API
refuses writes with 403. *Say:* "There is no API to edit or delete the audit log, even for an admin."

## 10. Health (30 s): *System Health*

Backend, ML model and simulator status, refreshed every 10 seconds.

---

## Questions you may be asked, and honest answers

**Is the AI real?** Yes when configured: a real language model (for example Llama 3.3 70B via Groq) writes the report from
the incident's real data. By default an offline analyst answers so the demo needs no key. Either way the report names who wrote
it, a real model's output is checked (MITRE comes from my mapping; invented IPs and technique ids are stripped), and if the
model fails the offline analyst answers instead.

**Is the data real?** No. Everything is synthetic, uses non-routable addresses and `.invalid` domains, and tests enforce that.

**Why Isolation Forest, and how accurate is it?** It needs no labels, which suits live telemetry. Accuracy is reported only
when a labelled dataset is used, and it is moderate on clustered attacks because that is a known weakness of the method.

**What would you do for production?** Authenticate the WebSocket, use a production web server instead of the Vite dev server,
real secrets and no demo accounts, real telemetry sources, and log denied requests to the audit trail. These are listed
under *Known limitations* in [architecture.md](architecture.md).

**How do you know it works?** 500+ automated backend tests on a real PostgreSQL and ~90 frontend tests, including a
mutation check (deliberately breaking code to confirm the tests notice), plus a test that a quiet network raises no alerts.

**Why are there no threat-intelligence lookups?** Synthetic indicators can't be looked up; the page says so, and
indicators are extracted into each investigation report so they could be.
