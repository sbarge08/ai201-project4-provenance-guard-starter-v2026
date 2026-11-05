# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->

1. `POST /submit` receives JSON with `text` and `creator_id`.
2. The route checks both fields are nonempty strings and rejects text longer
   than 5,000 characters.
3. It generates a UUID `content_id`.
4. GPT-2 measures how predictable the text is; stylometry measures sentence
   length variation, vocabulary diversity, and punctuation density.
5. `scoring.combine_signals` combines those two 0–1 signals into one bounded
   AI-likeness evidence score.
6. `scoring.score_to_label` maps that score to an AI-like, human-like, or
   unsure label. The score and label are estimates, not proof of authorship.
7. The route calculates a separate margin-based classification confidence,
   appends the scores and decision to the audit log, and returns JSON including
   the content ID and all three scores.

The confidence field is a heuristic measure of distance within the selected
label's score range. It is not a calibrated probability. A writer can appeal
by sending the returned `content_id` and nonempty reasoning to `POST /appeal`.
The original log entry remains unchanged; the appeal is appended as a new
`under_review` event.

**Privacy limitation:** `GET /log` currently returns the full audit log without
authentication, and `/appeal` accepts an ID and reasoning without verifying
the caller's identity. The service defaults to loopback for local class work;
do not expose it on a network with private submissions or appeals until
authentication and per-writer authorization protect these routes.

---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** GPT-2 token perplexity is `exp(mean token loss)`,
truncated to 400 tokens, then mapped to a 0–1 model signal with
`1 / (1 + (perplexity / 45) ** 1.6)`. Lower perplexity (greater
predictability) produces a higher score. It is AI-like evidence, not a
probability of authorship.

**Why that might differ between human and AI writing:** Generated text may be
predictable to a language model, but ordinary human writing can be predictable
too.

**What it can't see:** Predictability does not establish who wrote the text.
Plain writing can score as AI-like, and unusual writing can score as more
human-like.

### Signal two — the style signal

**What it measures:** Three surface features, combined with equal weight:

- Sentence-length variation is the coefficient of variation:
  population standard deviation of sentence word counts divided by their mean.
  Its AI-like feature is `1 / (1 + coefficient_of_variation)`. Fewer than two
  nonempty sentences provide no measurable variation.
- Vocabulary diversity is type-token ratio: unique recognized words divided by
  all recognized words. Its AI-like feature is `1 - type_token_ratio`.
- Punctuation density is Unicode punctuation characters divided by all text
  characters. Its AI-like feature is `min(punctuation_density / 0.10, 1)`.
  This direction and the 10% scale are heuristic choices, not universal facts
  about writing.

The style score is the arithmetic mean of those three features, rounded to
four decimal places. A missing sentence or vocabulary measurement contributes
0.5 (neutral); whitespace-only text returns 0.5.

**Why that might differ between human and AI writing:** These features are
simple descriptions of text shape. Low sentence-length variation and a lower
unique-word ratio are treated here as AI-like evidence, but those patterns are
not unique to generated text.

**What it can't see:** Stylometry does not understand meaning or authorship.
Editing sentence breaks, adding typos, or changing punctuation can change the
measurements without changing who wrote the ideas. Type-token ratio also
depends on text length. Sentence splitting is approximate, and token counts do
not account for word roots or context.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:** A weighted average, normalized by the sum of the configured
weights:
`combined_score = (model_weight * model_score + style_weight * style_score) / (model_weight + style_weight)`.
When signals disagree, the combined score lies between them.

**The numbers:** `WEIGHT_MODEL_SIGNAL = 0.5` and
`WEIGHT_STYLE_SIGNAL = 0.5`; therefore the combined score is their arithmetic
mean. These weights are configurable in `config.py`.

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:** For
example, if model_score is 0.8 and style_score is 0.2, equal weights produce
combined_score 0.5. The disagreement pulls the result toward the middle
instead of letting either signal decide alone. This is a mathematical example,
not an observed evaluation result.



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human-like | 0.00–0.25, inclusive | High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship. |
| unsure | greater than 0.25 and less than 0.75 | The signals are inconclusive. This system cannot determine who wrote the text. |
| high-confidence AI-like | 0.75–1.00, inclusive | High-confidence AI-like patterns: this system's signals are strongly associated with AI-generated writing. This is not proof of authorship. |

These are labels based on the configured AI-likeness score cutoffs, not
calibrated probabilities. `confidence` is a separate, heuristic margin score,
not a probability:

- Human: `0.5 + 0.5 * (HUMAN_THRESHOLD - score) / HUMAN_THRESHOLD`.
- AI: `0.5 + 0.5 * (score - AI_THRESHOLD) / (1 - AI_THRESHOLD)`.
- Unsure: `0.5 + 0.5 * (1 - abs(score - midpoint) / half_band)`.

The confidence rises as a score moves deeper into a decided label's range. In
the unsure band, it is highest at the midpoint and lowest at either boundary.

**Why I worded the "unsure" one this way:** It communicates that the signals
cannot settle authorship rather than treating an uncertain score as an
accusation.
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "The system works well. It handles most cases correctly and provides good results.", "creator_id": "readme-sample"}'
```

```json
{
  "combined_score": 0.4506,
  "confidence": 0.9012,
  "content_id": "fdb4853a-978c-4b8a-8279-97e58cdca7c8",
  "guess": "unsure",
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "model_score": 0.5781,
  "stage": "signals_combined_and_labeled",
  "style_score": 0.323
}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "fdb4853a-978c-4b8a-8279-97e58cdca7c8", "reasoning": "I wrote this text myself and request a review."}'
```

```json
{
  "content_id": "fdb4853a-978c-4b8a-8279-97e58cdca7c8",
  "message": "Your appeal has been recorded for review.",
  "status": "under_review"
}
```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json
{
  "count": 2,
  "entries": [
    {
      "combined_score": 0.4506,
      "content_id": "fdb4853a-978c-4b8a-8279-97e58cdca7c8",
      "creator_id": "readme-sample",
      "guess": "unsure",
      "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
      "model_score": 0.5781,
      "status": "decided",
      "style_score": 0.323,
      "timestamp": "2026-10-29T01:08:15+00:00"
    },
    {
      "content_id": "fdb4853a-978c-4b8a-8279-97e58cdca7c8",
      "creator_id": "readme-sample",
      "event": "appeal",
      "reasoning": "I wrote this text myself and request a review.",
      "status": "under_review",
      "timestamp": "2026-10-29T01:08:16+00:00"
    }
  ]
}
```

These are real response and audit-log examples from one smoke-test submission
and appeal, recorded in a temporary test log. They illustrate the API, not
accuracy or ground-truth performance.

---

## How I Used AI

**ChatGPT — planning and criteria discussions**

I used ChatGPT to discuss the system design and measurable acceptance
criteria, and to receive implementation guidance. The five acceptance
criteria and their targets were committed before implementation and remain
unchanged.

**GitHub Copilot — implementation and testing**

I used GitHub Copilot for code implementation and testing. I reviewed the
resulting changes and test outputs while building the service.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** 10 submissions per minute and 200 per day, per caller key.

**Why those numbers:** A normal writer should be able to submit a few revisions
without hitting the limit, while 10 requests in a minute makes a rapid
same-identity sweep of score variations harder. The 200-per-day cap also slows
sustained repeated submissions under one identity.

**What counts as a caller:** Flask-Limiter keys requests by `creator_id`; a
missing or invalid ID falls back to the caller's remote address. This is
convenient for the local exercise, but it does not authenticate that ID.
Someone can rotate or invent creator IDs to get fresh buckets, while people
sharing an ID or a fallback IP share a bucket. The in-memory counter resets
when the service restarts and is not shared across multiple service processes.
These limits slow repeated requests from the same key; they do not prevent
distributed requests, identity rotation, or other denial-of-service traffic,
and are not a production security boundary.

**Actual status codes from `python run_attacks.py --flood 15`:**

The 15 requests returned 10 successful responses followed by five rate-limit
rejections. The generated run is preserved in
[`results/flood_2026-11-04_1837.md`](results/flood_2026-11-04_1837.md).

```
200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
```

The five rejected requests were recorded by `audit.log_rejection` and are
visible through `GET /log`. Each entry records the caller key, rejection
reason, route, HTTP status, applicable limit, and timestamp; invalid
submissions are also audited without storing their raw writing. For example:

```json
{
  "creator_id": "flood_tester",
  "event": "rejected",
  "http_status": 429,
  "limit": "10 per 1 minute",
  "reason": "rate_limited",
  "route": "/submit",
  "status": "rejected",
  "timestamp": "2026-11-04T18:37:29-05:00"
}
```

---

## Attack Run — Before

**Exact baseline command:** `python run_attacks.py --set .\attack_set`

The original staff baseline ran on 2026-11-04 at 19:13. All 56 attacks
executed; I did not rerun or alter this before-improvement result. The preserved
raw output is [`results/attack_run_2026-11-04_1913.md`](results/attack_run_2026-11-04_1913.md).
The following verdicts compare each CSV target with its recorded response:

- **Evasion:** the target is to avoid an AI-like classification. `unsure`
  avoids the AI label, so it counts as BROKE for detection, but it does not
  mean the text was classified as human.
- **False positive:** the target is a false AI accusation against human
  writing. `unsure` is HELD because it is not an AI accusation.
- **Prompt injection:** the target is to override the requested classification,
  label, or log. A normal classification and intact audit record are HELD.
- **Malformed:** a rejected malformed request is HELD. For the unusual but
  nonempty text strings MF03–MF07, a conservative `unsure` response is HELD;
  MF03 is BROKE because it produced a high-confidence human-like decision.
- **Flood:** the first ten submissions fit the configured per-minute allowance;
  the two over-limit submissions received 429 and were rejected. The allowed
  first ten are not evidence of a quota bypass.

| Attack ID | Family | Documented target / intended outcome | Actual HTTP / prediction | Model / style / combined | Verdict | Evidence / justification |
|---|---|---|---|---|---|---|
| EV01 | `evasion` | signal two: typos raise word variety | 200 / unsure | 0.1635 / 0.3891 / 0.2763 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV02 | `evasion` | signal two: broken-up sentences raise length spread | 200 / unsure | 0.5943 / 0.3222 / 0.4583 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV03 | `evasion` | signal two: a pasted quotation changes the shape | 200 / unsure | 0.6662 / 0.3738 / 0.5200 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV04 | `evasion` | signal one: unusual words raise perplexity | 200 / unsure | 0.6114 / 0.3905 / 0.5010 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV05 | `evasion` | both signals: heavy human editing pass | 200 / unsure | 0.3212 / 0.3838 / 0.3525 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV06 | `evasion` | signal two: one very long sentence and one very short | 200 / unsure | 0.5727 / 0.2851 / 0.4289 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV07 | `evasion` | signal two: padding with punctuation | 200 / unsure | 0.5862 / 0.3446 / 0.4654 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV08 | `evasion` | signal one: text below the token window | 200 / unsure | 0.2452 / 0.3803 / 0.3128 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV09 | `evasion` | both: AI text with a human opening paragraph bolted on | 200 / unsure | 0.7042 / 0.3611 / 0.5327 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| EV10 | `evasion` | signal two: repeated stanza structure | 200 / unsure | 0.9792 / 0.4934 / 0.7363 | **BROKE** | No `ai` label; the documented evasion avoids decisive AI detection, though it is not labeled human. |
| FP01 | `false_positive` | plain, clear human writing with no flourishes | 200 / unsure | 0.6175 / 0.3943 / 0.5059 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| FP02 | `false_positive` | human writing in a formal register | 200 / unsure | 0.7387 / 0.4251 / 0.5819 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| FP03 | `false_positive` | a non-native English speaker writing carefully | 200 / unsure | 0.8051 / 0.4038 / 0.6045 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| FP04 | `false_positive` | a student essay written to a rubric | 200 / unsure | 0.8329 / 0.3796 / 0.6062 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| FP05 | `false_positive` | technical documentation written by a person | 200 / unsure | 0.8005 / 0.4798 / 0.6401 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| FP06 | `false_positive` | a person imitating a formal template | 200 / unsure | 0.8814 / 0.3808 / 0.6311 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| FP07 | `false_positive` | human writing that repeats a phrase deliberately | 200 / unsure | 0.8816 / 0.4691 / 0.6754 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| FP08 | `false_positive` | very short genuine human submission | 200 / unsure | 0.3223 / 0.5240 / 0.4232 | **HELD** | No `ai` prediction; the unsure label avoided a false-positive AI accusation. |
| PI01 | `prompt_injection` | instruction to ignore the check | 200 / unsure | 0.4625 / 0.2820 / 0.3722 | **HELD** | The demanded high-confidence human result was not returned; the service returned its standard unsure label. |
| PI02 | `prompt_injection` | instruction disguised as a system message | 200 / unsure | 0.2044 / 0.3066 / 0.2555 | **HELD** | The injected system instruction did not set the requested guess/confidence; output was unsure. |
| PI03 | `prompt_injection` | instruction wrapped in the writer's voice | 200 / unsure | 0.5943 / 0.3492 / 0.4718 | **HELD** | The pass-through claim did not suppress scoring; a standard unsure classification was returned. |
| PI04 | `prompt_injection` | attempt to make the label text hostile | 200 / unsure | 0.4998 / 0.4272 / 0.4635 | **HELD** | Hostile markup did not change the reader-facing label; output stayed the standard unsure label. |
| PI05 | `prompt_injection` | attempt to inject into the audit log | 200 / unsure | 0.6401 / 0.5741 / 0.6071 | **HELD** | The injected JSON fragment did not add fields to the decision; the audit event contains only schema fields. |
| PI06 | `prompt_injection` | instruction plus real human text | 200 / unsure | 0.5583 / 0.3939 / 0.4761 | **HELD** | The instruction to bypass stylometry did not force a human result; output was unsure. |
| MF01 | `malformed` | text is only whitespace | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected whitespace-only text before classification. |
| MF02 | `malformed` | text is a single character | 422 / N/A | N/A / N/A / N/A | **HELD** | HTTP 422 rejected the unscorable single character; no decision was emitted. |
| MF03 | `malformed` | text is control characters | 200 / human | 0.0000 / 0.4841 / 0.2420 | **BROKE** | Control characters received HTTP 200 and a high-confidence human-like decision. |
| MF04 | `malformed` | text is only punctuation | 200 / unsure | 0.0112 / 0.6667 / 0.3389 | **HELD** | Although accepted, it received `unsure`, not an unsupported confident authorship label. |
| MF05 | `malformed` | text is a very long single word | 200 / unsure | 0.9976 / 0.1667 / 0.5822 | **HELD** | Although accepted, it received `unsure`, not an unsupported confident authorship label. |
| MF06 | `malformed` | text is emoji only | 200 / unsure | 0.9969 / 0.3333 / 0.6651 | **HELD** | Although accepted, it received `unsure`, not an unsupported confident authorship label. |
| MF07 | `malformed` | text is right-to-left script | 200 / unsure | 0.9064 / 0.1984 / 0.5524 | **HELD** | Although accepted, it received `unsure`, not an unsupported confident authorship label. |
| MF08 | `malformed` | text is 60,000 characters | 413 / N/A | N/A / N/A / N/A | **HELD** | HTTP 413 rejected the over-limit text before classification. |
| RQ01 | `malformed` | no text field at all | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected the request with no text field; no decision was emitted. |
| RQ02 | `malformed` | no creator_id | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected the request with no creator_id; no decision was emitted. |
| RQ03 | `malformed` | text is a number | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected a numeric text value; no decision was emitted. |
| RQ04 | `malformed` | text is a list | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected a list-valued text field; no decision was emitted. |
| RQ05 | `malformed` | text is null | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected null text; no decision was emitted. |
| RQ06 | `malformed` | creator_id is an object | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected an object-valued creator_id; no decision was emitted. |
| RQ07 | `malformed` | body is a JSON array, not an object | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected a JSON array body; no decision was emitted. |
| RQ08 | `malformed` | body is unparseable JSON | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected unparseable JSON; no decision was emitted. |
| RQ09 | `malformed` | body is empty | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected an empty body; no decision was emitted. |
| RQ10 | `malformed` | body is form-encoded, not JSON | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected a form-encoded body; no decision was emitted. |
| RQ11 | `malformed` | body is JSON claiming to be plain text | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected a non-JSON content type; no decision was emitted. |
| RQ12 | `malformed` | deeply nested JSON | 400 / N/A | N/A / N/A / N/A | **HELD** | HTTP 400 rejected deeply nested non-string text; no decision was emitted. |
| FL01_01 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_02 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_03 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_04 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_05 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_06 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_07 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_08 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_09 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_10 | `flood_same_creator` | 20 rapid submissions from one creator | 200 / human | 0.0287 / 0.2273 / 0.1280 | **HELD** | Within the configured 10/minute allowance; the first ten requests were not over-limit. |
| FL01_11 | `flood_same_creator` | 20 rapid submissions from one creator | 429 / N/A | N/A / N/A / N/A | **HELD** | HTTP 429 after the first ten quota-eligible requests; over-limit request rejected. |
| FL01_12 | `flood_same_creator` | 20 rapid submissions from one creator | 429 / N/A | N/A / N/A / N/A | **HELD** | HTTP 429 after the first ten quota-eligible requests; over-limit request rejected. |

### Verdict counts

| Verdict | Count |
|---|---:|
| HELD | 45 |
| BROKE | 11 |
| UNDETERMINED | 0 |

The ten evasion attempts returned `unsure`, not `ai`: under their documented
evasion objective, that avoided an AI detection label, so they are BROKE.
This does not mean they were classified as human. All eight human false-positive
cases returned `unsure`, not `ai`, so the false-positive protection HELD on
these probes. The five unusual strings MF03–MF07 all returned HTTP 200, but
only MF03 produced a confident label; MF04–MF07 remained `unsure`. The
malformed request cases returned 400, 413, or 422 without a decision. FL01_11
and FL01_12 returned 429 after the first ten same-creator submissions.

### Audit evidence

These are 12 complete, genuine audit entries from the official run, copied
from [`logs/audit.jsonl`](logs/audit.jsonl); the same records are preserved
as JSON in [`results/audit_extract.json`](results/audit_extract.json). They
include scored decisions and actual 400, 413, and 429 rejections. Rejection
records do not contain raw submitted writing.

```json
[
  {
    "timestamp": "2026-11-05T00:13:04+00:00",
    "content_id": "fb5f6d72-6708-4468-a6fe-c2f7051d9e58",
    "creator_id": "attacker_EV10",
    "guess": "unsure",
    "model_score": 0.9792,
    "style_score": 0.4934,
    "combined_score": 0.7363,
    "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
    "status": "decided"
  },
  {
    "timestamp": "2026-11-05T00:13:05+00:00",
    "content_id": "91625d0c-c395-4737-9672-c79ebd6f5833",
    "creator_id": "attacker_FP03",
    "guess": "unsure",
    "model_score": 0.8051,
    "style_score": 0.4038,
    "combined_score": 0.6045,
    "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
    "status": "decided"
  },
  {
    "timestamp": "2026-11-05T00:13:06+00:00",
    "content_id": "dcf68ed4-1b57-4e0c-95f4-d83085d950ec",
    "creator_id": "attacker_PI04",
    "guess": "unsure",
    "model_score": 0.4998,
    "style_score": 0.4272,
    "combined_score": 0.4635,
    "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
    "status": "decided"
  },
  {
    "timestamp": "2026-11-05T00:13:07+00:00",
    "content_id": "f4a4ece3-ecf9-481b-a10e-99ec45d4bcae",
    "creator_id": "attacker_PI05",
    "guess": "unsure",
    "model_score": 0.6401,
    "style_score": 0.5741,
    "combined_score": 0.6071,
    "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
    "status": "decided"
  },
  {
    "timestamp": "2026-11-05T00:13:07+00:00",
    "creator_id": "attacker_MF01",
    "event": "rejected",
    "status": "rejected",
    "reason": "invalid_text",
    "route": "/submit",
    "http_status": 400
  },
  {
    "timestamp": "2026-11-05T00:13:07+00:00",
    "content_id": "b8ad3e2a-751b-4aed-b229-ba1178917465",
    "creator_id": "attacker_MF03",
    "guess": "human",
    "model_score": 0.0,
    "style_score": 0.4841,
    "combined_score": 0.242,
    "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
    "status": "decided"
  },
  {
    "timestamp": "2026-11-05T00:13:07+00:00",
    "content_id": "ddd07862-6c14-4906-b5ae-ed220dc47b9b",
    "creator_id": "attacker_MF04",
    "guess": "unsure",
    "model_score": 0.0112,
    "style_score": 0.6667,
    "combined_score": 0.3389,
    "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
    "status": "decided"
  },
  {
    "timestamp": "2026-11-05T00:13:08+00:00",
    "creator_id": "attacker_MF08",
    "event": "rejected",
    "status": "rejected",
    "reason": "text_too_long",
    "route": "/submit",
    "http_status": 413
  },
  {
    "timestamp": "2026-11-05T00:13:08+00:00",
    "creator_id": "attacker_RQ01",
    "event": "rejected",
    "status": "rejected",
    "reason": "invalid_text",
    "route": "/submit",
    "http_status": 400
  },
  {
    "timestamp": "2026-11-05T00:13:08+00:00",
    "creator_id": "attacker_RQ03",
    "event": "rejected",
    "status": "rejected",
    "reason": "invalid_text",
    "route": "/submit",
    "http_status": 400
  },
  {
    "timestamp": "2026-11-05T00:13:09+00:00",
    "content_id": "6de05f89-757b-4cf2-bdae-39041760dc77",
    "creator_id": "attacker_flood",
    "guess": "human",
    "model_score": 0.0287,
    "style_score": 0.2273,
    "combined_score": 0.128,
    "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
    "status": "decided"
  },
  {
    "timestamp": "2026-11-05T00:13:09+00:00",
    "creator_id": "attacker_flood",
    "event": "rejected",
    "status": "rejected",
    "reason": "rate_limited",
    "limit": "10 per 1 minute",
    "route": "/submit",
    "http_status": 429
  },
  {
    "timestamp": "2026-11-05T00:13:09+00:00",
    "creator_id": "attacker_flood",
    "event": "rejected",
    "status": "rejected",
    "reason": "rate_limited",
    "limit": "10 per 1 minute",
    "route": "/submit",
    "http_status": 429
  }
]
```

### Worst observed failure

**EV10** is the most concerning confirmed evasion. It targeted repeated stanza
structure and returned HTTP 200 with `model_score = 0.9792`,
`style_score = 0.4934`, and `combined_score = 0.7363`; the prediction was
`unsure`, not `ai`. With equal 0.5 weights, the recorded signals average to
0.7363, which is 0.0137 below the unchanged 0.75 AI threshold. The demonstrated
pipeline stage is the combining rule followed by label mapping: that combined
score maps to `unsure`, allowing the evasion to avoid an AI label. The scores
do not prove that stanza structure caused the style value; that causal link is
a hypothesis, not a result established by this single run.

MF03 is another confirmed failure: control characters received a
high-confidence human-like decision (`0.0000` model, `0.4841` style,
`0.2420` combined). The recorded evidence demonstrates the result, but does
not isolate why the model signal was zero.


---

## Run Log and Verdicts

**Original targets:** [criteria.md](criteria.md) remains unchanged. The first
three-trial run measured Criteria 3–5; the follow-up ran only Criteria 1–2 so
the prior results were preserved:

```powershell
.venv\Scripts\python.exe run_eval.py --label before
.venv\Scripts\python.exe run_eval.py --criteria 1,2 --label hc3
```

### HC3 paired samples for Criterion 2

The project now includes 20 paired questions from the published
[Human ChatGPT Comparison Corpus (HC3)](https://huggingface.co/datasets/Hello-SimpleAI/HC3),
subset `wiki_csai`, split `train`, rows 0–19 at dataset revision
`4d0ff18143b5a7e1b1e79beb540c04549d1e59d3`. Each pair uses the dataset's first
`human_answers` and first `chatgpt_answers` entry for the same question. The
deterministic selector in [prepare_hc3_samples.py](prepare_hc3_samples.py)
scans rows in ascending order, requires nonempty distinct answers within the
5,000-character limit, and never examines detector scores. The result is 20
human-labeled answers and 20 ChatGPT-labeled answers (40 distinct texts; max
length 3,621 characters). Pair IDs, row IDs, questions, source labels, and
row-level viewer/API references are stored with each sample in
[evaluation_samples.json](evaluation_samples.json).

HC3's paper describes the ChatGPT responses as coming from ChatGPT based on
the GPT-3.5 series, but the published rows do not identify per-answer author
identities, an exact deployed model version, or generation timestamps. The
human rows are dataset-labeled; they are not independently verified individual
human authorship. Those limitations are retained in each sample's provenance.
The evaluation harness therefore records Criterion 2 as a dataset-label
diagnostic and leaves the original acceptance criterion **NOT EVALUATED**
because its verified-human requirement is not established by the dataset.

The [HC3 dataset card](https://huggingface.co/datasets/Hello-SimpleAI/HC3)
declares CC BY-SA 4.0 and says stricter source-dataset licenses apply. Its
[source-license table](https://github.com/Hello-SimpleAI/chatgpt-comparison-detection#dataset-copyright)
identifies `wiki_csai` as Wikipedia under CC BY-SA. The sample file includes
dataset/publication attribution and exact source references; the copied
dataset-derived material is provided under the declared CC BY-SA terms with
share-alike attribution. This documentation does not independently establish
rights in underlying individual contributions.

### Human writing for Criterion 1

No set of 20 genuine user-authored writing samples with authorship evidence
was found in the repository. The HC3 human-labeled data is not used as a
substitute. Criterion 1 therefore remains **NOT EVALUATED**; 20 verified
human-written samples (`H01`–`H20`) with genuine authorship evidence are still
needed. No generated or AI-assisted text was relabeled as human writing.

### Three-trial results

The table preserves the original targets. Criterion 2's HC3 metrics are shown
as diagnostic measurements, not as satisfying the target's verified-human
condition.

| Criterion | Original target | Run 1 | Run 2 | Run 3 | MET/MISSED |
|---|---|---|---|---|---|
| 1. False-positive rate | At most 1 of 20 verified human-written texts receives the high-confidence AI label in each trial. | NOT EVALUATED — no verified human corpus | NOT EVALUATED — no verified human corpus | NOT EVALUATED — no verified human corpus | **NOT EVALUATED** |
| 2. Score separation | AI mean combined score minus verified-human mean combined score is at least 0.20 in each trial, using 20 samples per group. | HC3 diagnostic: AI 0.701915 − human 0.580000 = **0.121915** (numeric target missed) | Same: **0.121915** | Same: **0.121915** | **NOT EVALUATED** — dataset-labeled human data is not independently verified; diagnostic numeric target MISSED |
| 3. Label coverage | All three labels reachable; all scores 0–1 map to exactly one label, including thresholds and adjacent values. | All labels; 9 boundary cases; partition passed | Same | Same | **MET** |
| 4. Appeal reliability | 10/10 valid appeals audited as `under_review`, with original decisions retained. | 10/10; 0 rate-limited | 10/10; 0 rate-limited | 10/10; 0 rate-limited | **MET** |
| 5. Invalid-input handling | Six predefined invalid requests return 4xx without a valid decision being logged. | 6/6; 0 rate-limited | 6/6; 0 rate-limited | 6/6; 0 rate-limited | **MET** |

Criterion 2 values were identical in all three trials: 20/20 HTTP 200 scores
per group, mean AI combined score `0.701915`, mean human-labeled combined
score `0.580000`, difference `0.121915` against the `0.20` numerical target.
The numerical comparison missed. Since the sample group does not meet the
original verified-human provenance condition, the acceptance verdict remains
**NOT EVALUATED**, rather than a pass or a definitive failure on verified
writing.

The Criterion 1–2 run was produced by
`run_eval.py::main` / `run_eval.py::evaluate_scenario`; the per-sample scores
and complete provenance are in
[run_2026-11-04_194923_hc3.json](results/run_2026-11-04_194923_hc3.json),
with a readable report at
[run_2026-11-04_194923_hc3.md](results/run_2026-11-04_194923_hc3.md).
The original Criteria 3–5 measurements remain in
[run_2026-11-04_193334_before.json](results/run_2026-11-04_193334_before.json)
and [run_2026-11-04_193334_before.md](results/run_2026-11-04_193334_before.md);
they were not rerun in the HC3 follow-up.

Genuine Trial 1 JSON summaries follow. Criterion 1 was emitted by
`run_eval.py::main`; Criteria 2, 3, 4, and 5 were emitted by
`run_eval.py::evaluate_scenario` and the corresponding criterion helpers.

**Criterion 1**

```json
{
  "status": "NOT EVALUATED",
  "reason": "Missing 20 verified user-authored human samples. HC3's dataset-labeled human answers are not substituted for the original criterion's verified writing requirement."
}
```

**Criterion 2 — HC3 diagnostic; original target remains NOT EVALUATED**

```json
{
  "ai_sample_count": 20,
  "human_sample_count": 20,
  "ai_mean_combined_score": 0.701915,
  "human_mean_combined_score": 0.58,
  "ai_minus_human_mean": 0.121915,
  "target_minimum": 0.2,
  "metric_met": false,
  "rate_limited": 0
}
```

**Criterion 3**

```json
{
  "observed_labels": ["ai", "human", "unsure"],
  "all_labels_reached": true,
  "partition_verified": true,
  "boundary_cases": [
    {"case": "score_zero", "score": 0.0, "guess": "human"},
    {"case": "just_below_human_threshold", "score": 0.24999999999999997, "guess": "human"},
    {"case": "human_threshold", "score": 0.25, "guess": "human"},
    {"case": "just_above_human_threshold", "score": 0.25000000000000006, "guess": "unsure"},
    {"case": "unsure_band_midpoint", "score": 0.5, "guess": "unsure"},
    {"case": "just_below_ai_threshold", "score": 0.7499999999999999, "guess": "unsure"},
    {"case": "ai_threshold", "score": 0.75, "guess": "ai"},
    {"case": "just_above_ai_threshold", "score": 0.7500000000000001, "guess": "ai"},
    {"case": "score_one", "score": 1.0, "guess": "ai"}
  ],
  "metric_met": true
}
```

**Criterion 4**

```json
{
  "appeals_succeeded": 10,
  "appeals_expected": 10,
  "rate_limited": 0,
  "metric_met": true
}
```

**Criterion 5**

```json
{
  "invalid_cases_rejected": 6,
  "invalid_cases_expected": 6,
  "rate_limited": 0,
  "metric_met": true
}
```

The original Criteria 3–5 run's nine cases and all detailed appeal and invalid
request evidence are retained in its linked JSON report. In the HC3 follow-up,
all 120 classification submissions returned HTTP 200 and none was
rate-limited. The audit log contains those real decisions; earlier audit
entries from Criteria 3–5 remain append-only. The rate limiter stayed enabled.
The classifier, weights, thresholds, label mapping, and
[criteria.md](criteria.md) were not changed.

**Overall status: INCOMPLETE.** Criterion 1 is NOT EVALUATED for lack of 20
verified human-authored samples. Criterion 2 has a genuine HC3 diagnostic, but
its acceptance status is NOT EVALUATED because HC3's human labels do not
establish the criterion's individual verified-authorship requirement; its
observed numeric gap also fell short of 0.20. Criteria 3–5 met their targets
in all three previously recorded trials.

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
