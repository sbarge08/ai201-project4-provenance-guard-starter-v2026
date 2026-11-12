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
| unsure | greater than 0.25 and less than 0.73 | The signals are inconclusive. This system cannot determine who wrote the text. |
| high-confidence AI-like | 0.73–1.00, inclusive | High-confidence AI-like patterns: this system's signals are strongly associated with AI-generated writing. This is not proof of authorship. |

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
unchanged. During Unit 8, I also used AI assistance to reason about attack
objectives, evaluate whether recorded responses met those objectives, and
draft documentation from the saved attack and evaluation records. I reviewed
the results against the actual files rather than treating generated analysis
as evidence. I did not relabel uncertain or AI-assisted writing as verified
human text; the missing verified-human samples remain an explicit limitation.

**GitHub Copilot — implementation and testing**

I used GitHub Copilot for implementation, evaluation-harness work,
documentation, and local test execution. In Milestone 5, the only production
change was the requested `AI_THRESHOLD` adjustment from 0.75 to 0.73. I
reviewed the diff, attack outcomes, saved evaluation reports, audit evidence,
and test output. The original attack baseline and `criteria.md` were preserved.

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

**Baseline verdict reconciliation:** 45 HELD and 11 BROKE. The 11 broken
IDs are **EV01–EV10 and MF03**: ten evasion cases returned `unsure`, and the
additional MF03 control-character case returned a high-confidence `human`
label. The Milestone 4 failure list includes all eleven; MF03 is the one
non-evasion failure.

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

---

## Milestone 4 — Verdicts and Failure Diagnosis

This section interprets the preserved Milestone 3 outputs and the original
56-attack baseline. It makes no claim that a missing or dataset-labeled sample
is verified authorship. The original targets are quoted from
[criteria.md](criteria.md); the records are
[run_2026-11-04_193334_before.json](results/run_2026-11-04_193334_before.json),
[run_2026-11-04_194923_hc3.json](results/run_2026-11-04_194923_hc3.json), and
[attack_run_2026-11-04_1913.md](results/attack_run_2026-11-04_1913.md).

### Verdicts against the five original criteria

| Criterion | Exact original target | Trial 1 | Trial 2 | Trial 3 | Verdict and evidence |
|---|---|---|---|---|---|
| 1. False-positive rate | “Of 20 verified human-written texts, at most one may receive the high-confidence AI label in each of three trials.” | NOT EVALUATED | NOT EVALUATED | NOT EVALUATED | **NOT EVALUATED.** Both runs record that 20 verified human samples are unavailable. HC3 human-labeled answers do not establish individually verified human authorship, and no false-positive rate for the required group was measured. |
| 2. Score separation | “The average combined AI-likeness score for 20 known AI-generated texts must exceed the average for 20 verified human-written texts by at least 0.20 in each of three trials.” | NOT EVALUATED; HC3 diagnostic gap 0.121915 | NOT EVALUATED; HC3 diagnostic gap 0.121915 | NOT EVALUATED; HC3 diagnostic gap 0.121915 | **NOT EVALUATED.** The HC3 diagnostic used 20 ChatGPT-labeled and 20 dataset-labeled human answers, not the criterion's verified-human set. Its measured means were AI 0.701915 and human-labeled 0.580000; the difference 0.121915 numerically falls short of 0.20 in each trial, but is not a valid measurement of the original criterion. |
| 3. Label coverage | “All three labels (`ai`, `human`, `unsure`) must be reachable, and every combined score from 0 through 1 must map to exactly one label.” | MET — all three labels, partition verified, 9 boundary cases | MET — same | MET — same | **MET.** The stored result marks `all_labels_reached`, `partition_verified`, and `metric_met` true in all three trials. Exact thresholds and immediately adjacent floating-point values were included. |
| 4. Appeal reliability | “All 10 valid appeals in each of three trials must be recorded and move their corresponding submission to `under_review`.” | MET — 10/10, 0 rate-limited | MET — 10/10, 0 rate-limited | MET — 10/10, 0 rate-limited | **MET.** All three stored trial summaries record 10 successful appeals of 10 expected and no rate limiting. |
| 5. Invalid-input handling | “All six predefined invalid requests must receive an appropriate HTTP 4xx response and must not create a valid decision record, in every one of three trials.” | MET — 6/6, 0 rate-limited | MET — 6/6, 0 rate-limited | MET — 6/6, 0 rate-limited | **MET.** All three summaries record six rejected cases of six expected and no rate limiting. The runner also checked that no valid decision was logged for those requests. |

The evaluator result sets preserve the evidence for these verdicts. The
`before` run contains the three Criterion 3–5 trials and marks Criteria 1–2
NOT EVALUATED for missing data. The separate `hc3` run records the three
HC3-only Criterion 2 diagnostic measurements, while retaining NOT EVALUATED
as the acceptance verdict for Criteria 1–2. No missing result is treated as
a pass or a measured failure.

### Diagnosis of all 11 BROKE attacks

The baseline contains ten evasion failures and one malformed-input failure.
The “actual result” values below are the recorded HTTP response and scores;
the targets are the attack CSV's documented objectives. For accepted
submissions, `unsure` means no decisive AI label was produced, not that the
text was judged human. In every evasion row the demonstrated common path is
that the returned combined score was below the configured 0.75 AI threshold
and `scoring.score_to_label` consequently returned `unsure`. The baseline
records signal outputs, but not raw perplexity or the three separate
stylometry feature values. An attack's intended manipulation is not, by
itself, proof that it caused a particular signal value.

| Attack | Objective in attack set | Actual status, scores, returned label | Pipeline stage and evidence-based mechanism | Remaining uncertainty |
|---|---|---|---|---|
| EV01 | Typos raise word variety (stylometry) | HTTP 200; model 0.1635, style 0.3891, combined 0.2763; `unsure` | **Stylometry signal → combination → label mapping.** The measured combined score is below 0.75, so the label mapper returns `unsure`. The measured model score is also low; equal weighting yields 0.2763. | No clean paired input or logged type-token ratio isolates the effect of the typos. |
| EV02 | Broken-up sentences raise sentence-length variation (stylometry) | HTTP 200; model 0.5943, style 0.3222, combined 0.4583; `unsure` | **Stylometry signal → combination → label mapping.** The measured style score is 0.3222 and the mean of the two signals is 0.4583, below the AI threshold. | Sentence-length component values and an unmodified comparison are absent, so the causal effect of the added short sentences is not measured. |
| EV03 | A pasted quotation changes the text shape (stylometry) | HTTP 200; model 0.6662, style 0.3738, combined 0.5200; `unsure` | **Stylometry signal → combination → label mapping.** Despite the quoted passage, recorded style and combined scores leave the result in the unsure interval. | The baseline has no pre-quotation control or per-feature style breakdown; the quotation's isolated effect is unknown. |
| EV04 | Unusual words raise GPT-2 perplexity (model signal) | HTTP 200; model 0.6114, style 0.3905, combined 0.5010; `unsure` | **GPT-2 signal → combination → label mapping.** The model signal recorded for this input is 0.6114, not enough to place the combined score at 0.75; the style score brings the equal-weight result to 0.5010. | Perplexity itself is not recorded, and there is no ordinary-word control. The record cannot show whether the unusual words increased perplexity relative to a baseline. |
| EV05 | Heavy human editing changes both signals | HTTP 200; model 0.3212, style 0.3838, combined 0.3525; `unsure` | **Both signal stages → combination → label mapping.** Both recorded inputs to the equal-weight mean are below 0.5, resulting in a combined score well below the AI threshold. | There is no unedited counterpart or provenance experiment proving the passage was generated then edited; only the attack's stated objective and returned measurements are available. |
| EV06 | One very long sentence and one very short sentence change sentence-length variation | HTTP 200; model 0.5727, style 0.2851, combined 0.4289; `unsure` | **Stylometry signal → combination → label mapping.** The style score is 0.2851 and the combined result remains below 0.75. | The component sentence lengths were not separately logged, and no paired control establishes how much this structure changed the style score. |
| EV07 | Punctuation padding changes punctuation density (stylometry) | HTTP 200; model 0.5862, style 0.3446, combined 0.4654; `unsure` | **Stylometry signal → combination → label mapping.** The punctuation-padded input still received a 0.3446 style score; averaging it with 0.5862 gives 0.4654, not an AI label. | The punctuation-density feature and a version without padding were not separately recorded; the target's claimed effect is not isolated. |
| EV08 | Text below the model token window evades signal one | HTTP 200; model 0.2452, style 0.3803, combined 0.3128; `unsure` | **GPT-2 signal → combination → label mapping.** The model signal is low for the submitted short text, producing a combined score in the unsure range. The route accepted and scored it. | The record has no token count or perplexity. It does not establish that being below the 400-token truncation limit caused the model score; the configured maximum is not evidence of a minimum-length check. |
| EV09 | AI text with a human-sounding opening paragraph (both signals) | HTTP 200; model 0.7042, style 0.3611, combined 0.5327; `unsure` | **Both signal stages → combination → label mapping.** The recorded style score is lower than the model score; equal weighting yields 0.5327, below the AI cutoff. | No result for the AI body alone or the opening paragraph alone is recorded, so the relative causal contribution of each part is unknown. |
| EV10 | Repeated stanza structure changes stylometry | HTTP 200; model 0.9792, style 0.4934, combined 0.7363; `unsure` | **Signal combination → label mapping** is the demonstrated miss. With equal 0.5 weights, `(0.9792 + 0.4934) / 2 = 0.7363`; `score_to_label` maps scores below 0.75 and above 0.25 to `unsure`. The score is 0.0137 below the AI threshold. | The result establishes the numeric/style outputs for this submission, not that stanza formatting caused style score 0.4934. The raw three style components and an otherwise identical control were not recorded. |
| MF03 | Control-character input should not be classified as ordinary writing | HTTP 200; model 0.0000, style 0.4841, combined 0.2420; `human` | **Route and validation** is the actionable failure. `app.submit` checks that `text` is a nonempty string and at most 5,000 characters; this mixed control/printable string passed those checks and proceeded to both signals. With equal weights, the recorded signals average to 0.24205, rounded to 0.2420. Since 0.2420 is at or below the 0.25 human threshold, the label mapper returns a confident human-like label. | The response demonstrates the confident label for this control-character input. The baseline does not log GPT-2 perplexity or the reason `model_signal` saturated at 0.0000, so that signal's internal cause is not established. |

**EV10 arithmetic in detail:** the unchanged configuration gives each signal
weight 0.5. The weighted average is
`(0.5 × 0.9792 + 0.5 × 0.4934) / (0.5 + 0.5) = 0.7363`.
The label boundary is inclusive at 0.75 for `ai`; because 0.7363 is below
that boundary and above 0.25, the current rule maps it to `unsure`. The
recorded style score alone does not establish that repeated stanza formatting
caused it.

**MF03 route evidence:** the attack CSV input is
`\u0000\u0001\u0002 test \u001b[31mred\u001b[0m`. The route's text validation
requires a string with non-whitespace content and enforces a 5,000-character
maximum; it does not require printable prose or recognized words. The input
therefore reached classification and was recorded as a decision instead of
being rejected as unsuitable text.

### Common mechanisms and priority

- **10 of 11 failures (EV01–EV10) are evasion cases.** Six target
  surface-style features, two target changes across both signals, and two
  target the model signal. Their common measured outcome is a
  combined score below 0.75, hence an `unsure` label instead of an AI label.
  The most frequent *pipeline* mechanism is the combination and label-mapping
  path not reaching a decisive AI score on modified AI text. Without paired
  controls and component-level logs, the attacks' causal effects on individual
  signals are not demonstrated.
- **MF03 is the remaining failure.** Validation accepts nonempty control
  characters; the resulting anomalous model score then pulls the average
  into the human-labeled range. This is separate from the ten evasion cases.
- **Most important Milestone 5 problem:** prevent evasive AI-like submissions
  from avoiding a decisive AI result while preserving conservative treatment
  of human writing. EV10 is the clearest single demonstration: the model
  signal is 0.9792, yet the equal-weight combination is just below the AI
  cutoff. Any more aggressive decision must be evaluated against the missing
  verified-human criterion rather than presumed safe. MF03 also warrants a
  focused input-validation check.

### Two one-change proposals considered before Milestone 5

At the end of Milestone 4, these were unimplemented alternatives. Milestone 5
now measures the first proposal only.

1. **Lower `config.AI_THRESHOLD` from 0.75 to 0.73.** This is one
   configuration-value change. EV10's recorded 0.7363 would map to `ai`
   under the existing `>= AI_THRESHOLD` rule. The tradeoff is that more
   borderline human writing may receive a high-confidence AI-like label.
   Criterion 1 is directly at risk; Criterion 3's boundaries must be
   re-evaluated, although the three-label contiguous partition remains
   structurally possible. Criterion 2's combined-score metric is unchanged
   by a label-only threshold change; appeal and invalid-input behavior are
   not directly changed.
2. **Reduce `config.WEIGHT_STYLE_SIGNAL` from 0.5 to 0.4, leaving
   `WEIGHT_MODEL_SIGNAL` at 0.5.** This changes one parameter; the existing
   normalization then makes the model signal's share 0.5/0.9. On EV10's
   recorded scores the resulting weighted mean would be approximately 0.7633,
   above 0.75. This makes the model signal more influential but may make
   style-targeted attacks less effective; it also changes scores for every
   submission and could increase false AI labels. Criteria 1 and 2 require
   fresh trials, and Criterion 3 should be rechecked even though its
   thresholds are unchanged. Criteria 4 and 5 do not directly measure the
   changed scoring rule.

Neither proposal's expected behavior above is represented as a result; the
threshold experiment's actual results are recorded below.

---

## The Improvement

**What changed:** exactly one production parameter changed in
[`config.py`](config.py): `AI_THRESHOLD` from `0.75` to `0.73`. The GPT-2
detector, stylometry, signal weights, human threshold, validation, rate
limiting, audit logging, and original criteria are unchanged.

**Which diagnosis pointed at it:** EV10 was the clearest evasion in the
before run: model `0.9792`, style `0.4934`, combined `0.7363`, and `unsure`.
The equal-weight arithmetic is `(0.9792 + 0.4934) / 2 = 0.7363`, just below
the old inclusive AI threshold of `0.75`. The lower boundary is intended to
make that score AI-like evidence. MF03 also broke before, but is deliberately
not separately fixed in this experiment.

**Hypothesis:** with only this threshold adjustment, EV10 will change from
`unsure` to `ai`; some borderline human submissions could also change to
`ai`, increasing false-positive risk. Scores themselves should remain the
same because this is a label-boundary change.

### Attack Run — After

**Exact command:** `python run_attacks.py --set .\attack_set --label after`

The full 56-attack run completed on 2026-11-04 at 20:41. Its unannotated,
runner-generated record is
[`results/attack_run_2026-11-04_2041_after.md`](results/attack_run_2026-11-04_2041_after.md).
The five-criteria rerun used the exact command
`python run_eval.py --label after`.
The verdicts and before/after values below use the same family-specific
judgment rules as the original run. The runner records component scores and
confidence but does not include `combined_score` in its per-attack JSON;
combined scores in this comparison were recomputed with unchanged
`scoring.combine_signals` from the recorded model/style scores and match the
audit entries. `—` means the request was rejected before scoring.

**Full Attack Run — After and before/after comparison**

| ID | Family / documented objective | Before: HTTP / guess / combined | Before | After: HTTP / guess / combined | After | Change |
|---|---|---|---|---|---|---|
| EV01 | evasion: signal two: typos raise word variety | 200/unsure/0.2763 | BROKE | 200/unsure/0.2763 | BROKE | stayed the same |
| EV02 | evasion: signal two: broken-up sentences raise length spread | 200/unsure/0.4583 | BROKE | 200/unsure/0.4583 | BROKE | stayed the same |
| EV03 | evasion: signal two: a pasted quotation changes the shape | 200/unsure/0.5200 | BROKE | 200/unsure/0.5200 | BROKE | stayed the same |
| EV04 | evasion: signal one: unusual words raise perplexity | 200/unsure/0.5010 | BROKE | 200/unsure/0.5010 | BROKE | stayed the same |
| EV05 | evasion: both signals: heavy human editing pass | 200/unsure/0.3525 | BROKE | 200/unsure/0.3525 | BROKE | stayed the same |
| EV06 | evasion: signal two: one very long sentence and one very short | 200/unsure/0.4289 | BROKE | 200/unsure/0.4289 | BROKE | stayed the same |
| EV07 | evasion: signal two: padding with punctuation | 200/unsure/0.4654 | BROKE | 200/unsure/0.4654 | BROKE | stayed the same |
| EV08 | evasion: signal one: text below the token window | 200/unsure/0.3128 | BROKE | 200/unsure/0.3128 | BROKE | stayed the same |
| EV09 | evasion: both: AI text with a human opening paragraph bolted on | 200/unsure/0.5327 | BROKE | 200/unsure/0.5327 | BROKE | stayed the same |
| EV10 | evasion: signal two: repeated stanza structure | 200/unsure/0.7363 | BROKE | 200/ai/0.7363 | HELD | improved |
| FP01 | false_positive: plain, clear human writing with no flourishes | 200/unsure/0.5059 | HELD | 200/unsure/0.5059 | HELD | stayed the same |
| FP02 | false_positive: human writing in a formal register | 200/unsure/0.5819 | HELD | 200/unsure/0.5819 | HELD | stayed the same |
| FP03 | false_positive: a non-native English speaker writing carefully | 200/unsure/0.6045 | HELD | 200/unsure/0.6045 | HELD | stayed the same |
| FP04 | false_positive: a student essay written to a rubric | 200/unsure/0.6062 | HELD | 200/unsure/0.6062 | HELD | stayed the same |
| FP05 | false_positive: technical documentation written by a person | 200/unsure/0.6401 | HELD | 200/unsure/0.6401 | HELD | stayed the same |
| FP06 | false_positive: a person imitating a formal template | 200/unsure/0.6311 | HELD | 200/unsure/0.6311 | HELD | stayed the same |
| FP07 | false_positive: human writing that repeats a phrase deliberately | 200/unsure/0.6754 | HELD | 200/unsure/0.6754 | HELD | stayed the same |
| FP08 | false_positive: very short genuine human submission | 200/unsure/0.4232 | HELD | 200/unsure/0.4232 | HELD | stayed the same |
| PI01 | prompt_injection: instruction to ignore the check | 200/unsure/0.3722 | HELD | 200/unsure/0.3722 | HELD | stayed the same |
| PI02 | prompt_injection: instruction disguised as a system message | 200/unsure/0.2555 | HELD | 200/unsure/0.2555 | HELD | stayed the same |
| PI03 | prompt_injection: instruction wrapped in the writer's voice | 200/unsure/0.4718 | HELD | 200/unsure/0.4718 | HELD | stayed the same |
| PI04 | prompt_injection: attempt to make the label text hostile | 200/unsure/0.4635 | HELD | 200/unsure/0.4635 | HELD | stayed the same |
| PI05 | prompt_injection: attempt to inject into the audit log | 200/unsure/0.6071 | HELD | 200/unsure/0.6071 | HELD | stayed the same |
| PI06 | prompt_injection: instruction plus real human text | 200/unsure/0.4761 | HELD | 200/unsure/0.4761 | HELD | stayed the same |
| MF01 | malformed: text is only whitespace | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| MF02 | malformed: text is a single character | 422/—/— | HELD | 422/—/— | HELD | stayed the same |
| MF03 | malformed: text is control characters | 200/human/0.2420 | BROKE | 200/human/0.2420 | BROKE | stayed the same |
| MF04 | malformed: text is only punctuation | 200/unsure/0.3389 | HELD | 200/unsure/0.3389 | HELD | stayed the same |
| MF05 | malformed: text is a very long single word | 200/unsure/0.5822 | HELD | 200/unsure/0.5822 | HELD | stayed the same |
| MF06 | malformed: text is emoji only | 200/unsure/0.6651 | HELD | 200/unsure/0.6651 | HELD | stayed the same |
| MF07 | malformed: text is right-to-left script | 200/unsure/0.5524 | HELD | 200/unsure/0.5524 | HELD | stayed the same |
| MF08 | malformed: text is 60,000 characters | 413/—/— | HELD | 413/—/— | HELD | stayed the same |
| RQ01 | malformed: no text field at all | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ02 | malformed: no creator_id | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ03 | malformed: text is a number | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ04 | malformed: text is a list | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ05 | malformed: text is null | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ06 | malformed: creator_id is an object | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ07 | malformed: body is a JSON array, not an object | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ08 | malformed: body is unparseable JSON | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ09 | malformed: body is empty | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ10 | malformed: body is form-encoded, not JSON | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ11 | malformed: body is JSON claiming to be plain text | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| RQ12 | malformed: deeply nested JSON | 400/—/— | HELD | 400/—/— | HELD | stayed the same |
| FL01_01 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_02 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_03 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_04 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_05 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_06 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_07 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_08 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_09 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_10 | flood_same_creator: 20 rapid submissions from one creator | 200/human/0.1280 | HELD | 200/human/0.1280 | HELD | stayed the same |
| FL01_11 | flood_same_creator: 20 rapid submissions from one creator | 429/—/— | HELD | 429/—/— | HELD | stayed the same |
| FL01_12 | flood_same_creator: 20 rapid submissions from one creator | 429/—/— | HELD | 429/—/— | HELD | stayed the same |

Before/after family totals: evasion **0/10 → 1/10 HELD**; false-positive
attacks **8/8 → 8/8 HELD** (zero `ai` labels in both runs); prompt injection
**6/6 → 6/6 HELD**; malformed **19/20 → 19/20 HELD** (MF03 remained BROKE);
flood **12/12 → 12/12 HELD** (ten allowed submissions and two HTTP 429s).
Overall, the baseline was **45 HELD / 11 BROKE**, and after was **46 HELD /
10 BROKE**. **EV10 improved** from BROKE to HELD; no attack became worse.

**Did it help, and how do I know?** It helped against the specific EV10
evasion: same recorded model `0.9792`, style `0.4934`, and combined `0.7363`,
but its returned guess changed from `unsure` to `ai` at threshold 0.73. The
other nine evasions stayed `unsure`, MF03 stayed a confident `human`, and no
other verdict changed. This is a one-attack improvement in the staff set, not
evidence of general detection accuracy.

### Before/after three-trial acceptance criteria

The original target text remains in [criteria.md](criteria.md), unchanged.
“Before” references the original three-trial run and the separate HC3
diagnostic; “after” references
[`results/run_2026-11-04_204406_after.json`](results/run_2026-11-04_204406_after.json).
Criteria 1–2 remain NOT EVALUATED for the original acceptance criteria
because the required verified-human authorship evidence is unavailable.

| Criterion and original target | Before trial 1 | Before trial 2 | Before trial 3 | After trial 1 | After trial 2 | After trial 3 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. At most 1 of 20 verified human-written texts receives the high-confidence AI label in each trial. | NOT EVALUATED: no verified human corpus | NOT EVALUATED: no verified human corpus | NOT EVALUATED: no verified human corpus | NOT EVALUATED: no verified human corpus | NOT EVALUATED: no verified human corpus | NOT EVALUATED: no verified human corpus | **NOT EVALUATED** |
| 2. AI mean combined score minus verified-human mean is at least 0.20 in each trial, using 20 samples per group. | NOT EVALUATED; HC3 diagnostic gap 0.121915 | NOT EVALUATED; HC3 diagnostic gap 0.121915 | NOT EVALUATED; HC3 diagnostic gap 0.121915 | NOT EVALUATED; HC3 diagnostic gap 0.121915 | NOT EVALUATED; HC3 diagnostic gap 0.121915 | NOT EVALUATED; HC3 diagnostic gap 0.121915 | **NOT EVALUATED** |
| 3. All three labels reachable; every score 0–1 maps to exactly one label, including thresholds and adjacent values. | MET; 9 cases, AI boundary 0.75, partition true | MET; 9 cases, AI boundary 0.75, partition true | MET; 9 cases, AI boundary 0.75, partition true | MET; 9 cases, AI boundary 0.73, partition true | MET; 9 cases, AI boundary 0.73, partition true | MET; 9 cases, AI boundary 0.73, partition true | **MET** |
| 4. All 10 valid appeals in each trial are recorded as `under_review`, and original decisions remain. | MET; 10/10, 0 rate-limited | MET; 10/10, 0 rate-limited | MET; 10/10, 0 rate-limited | MET; 10/10, 0 rate-limited | MET; 10/10, 0 rate-limited | MET; 10/10, 0 rate-limited | **MET** |
| 5. All six predefined invalid requests receive 4xx responses and create no valid decision in each trial. | MET; 6/6, 0 rate-limited | MET; 6/6, 0 rate-limited | MET; 6/6, 0 rate-limited | MET; 6/6, 0 rate-limited | MET; 6/6, 0 rate-limited | MET; 6/6, 0 rate-limited | **MET** |

**Criterion 2 HC3 diagnostic before/after (exploratory, not verified-authorship
acceptance testing):** In all three before trials and all three after trials,
20 AI-labeled and 20 human-labeled dataset answers were scored. Both runs
measured AI mean `0.701915`, human-labeled mean `0.580000`, and gap
`0.121915` against the exploratory numeric comparison target of `0.20`;
`metric_met` was false. The threshold change does not change combined scores,
and HC3 does not independently verify each human respondent. Therefore the
original Criterion 2 remains NOT EVALUATED, not MET or MISSED on verified
human evidence. Criterion 1 also remains NOT EVALUATED; 20 verified
human-authored samples are still missing.

**False-positive tradeoff:** the eight staff false-positive probes remained
`unsure` and none became `ai`, so this attack run showed no regression in that
family. These probes are not the 20 verified human samples required by
Criterion 1. Lowering the threshold expands the AI-labeled interval by 0.02
and contracts the unsure interval; it may label other borderline human text
as AI-like. The available evidence cannot measure that risk or establish that
the change is safe for human writers.

**Audit and result evidence:** the extracted after-run audit events are in
[`results/audit_extract_after.json`](results/audit_extract_after.json),
including the EV10 decision, malformed outcomes, flood 429 rejections, and
evaluation events. The complete comparison data, including model and style
scores, is in
[`results/attack_comparison_after.json`](results/attack_comparison_after.json).

---

## What's Still Broken

The after run has ten remaining BROKE cases. The nine evasion failures and
MF03 are listed individually below; all exact scores are from
[`results/attack_comparison_after.json`](results/attack_comparison_after.json).
The one-parameter change fixed EV10 only. For EV01–EV09 the returned combined
score remained below the new inclusive 0.73 AI threshold, so the existing
label mapper returned `unsure`. That avoids an AI accusation but also means
the intended evasions avoid decisive AI detection. The targeted signal
manipulations are the attack objectives; without paired control inputs, their
individual causal effects are not proven.

| Attack | Objective and actual after result | Remaining failure / next evidence |
|---|---|---|
| EV01 | Typos / word variety; HTTP 200, model 0.1635, style 0.3891, combined 0.2763, `unsure` | Evasion remains inconclusive. Compare the typo version with its unmodified counterpart and inspect the style features before attributing the score to spelling changes. |
| EV02 | Broken-up sentences / sentence-length variation; HTTP 200, model 0.5943, style 0.3222, combined 0.4583, `unsure` | Evasion remains inconclusive. A paired version and recorded sentence-length feature are needed to measure the structural effect. |
| EV03 | Pasted quotation / text shape; HTTP 200, model 0.6662, style 0.3738, combined 0.5200, `unsure` | Evasion remains inconclusive. Compare the same passage before and after the quotation; current evidence does not isolate its effect. |
| EV04 | Unusual words / GPT-2 perplexity; HTTP 200, model 0.6114, style 0.3905, combined 0.5010, `unsure` | Evasion remains inconclusive. The run did not record perplexity or an ordinary-word control, so the claimed model-signal effect is uncertain. |
| EV05 | Heavy human editing / both signals; HTTP 200, model 0.3212, style 0.3838, combined 0.3525, `unsure` | Both measured signals produce a low combined score. An unedited, provenance-matched control is needed to separate editing effects from the original text. |
| EV06 | One very long and one very short sentence / stylometry; HTTP 200, model 0.5727, style 0.2851, combined 0.4289, `unsure` | Evasion remains inconclusive. Sentence-length feature values and a paired input were not captured, so the stated mechanism is unverified. |
| EV07 | Punctuation padding / punctuation density; HTTP 200, model 0.5862, style 0.3446, combined 0.4654, `unsure` | Evasion remains inconclusive. Compare with the same text without padding and record the punctuation component before attributing the result. |
| EV08 | Text below the model token window; HTTP 200, model 0.2452, style 0.3803, combined 0.3128, `unsure` | Evasion remains inconclusive. The submitted short text is accepted; the recorded output has no token count or perplexity to establish why the model score is low. |
| EV09 | AI text with a human-sounding opening / both signals; HTTP 200, model 0.7042, style 0.3611, combined 0.5327, `unsure` | Evasion remains inconclusive. Separate scores for the opening and AI body would be needed to determine their contributions. |
| MF03 | Control-character-containing input; HTTP 200, model 0.0000, style 0.4841, combined 0.2420, `human` | The route accepts this nonempty string and emits a confident human-like decision. The model score's internal cause is unknown; validation should be assessed with explicit non-printable-input cases before a separate fix. |

### Criteria that remain unevaluated

- **Criterion 1 — false-positive limit:** NOT EVALUATED before and after.
  There are not 20 verified human-written samples with adequate authorship
  evidence. The eight staff false-positive probes are not a substitute for
  the fixed verified-human evaluation set.
- **Criterion 2 — score separation:** NOT EVALUATED before and after against
  the original criterion, because the HC3 human answers are dataset-labeled
  rather than independently verified as human-authored. The HC3 comparison
  is an exploratory diagnostic only: each before and after trial measured an
  AI mean of 0.701915, human-labeled mean of 0.580000, and gap of 0.121915,
  below the numerical target 0.20. No verified-human result can be inferred
  from that gap.

Criteria 3–5 were MET in all three before and all three after trials. The
label-boundary checks used 0.75 before and 0.73 after; all labels remained
reachable and the partition remained complete. Appeals remained 10/10 and
invalid requests 6/6 in each trial, with no rate limiting.

**What I would fix next and why I stopped:** First, I would obtain the
20 genuinely verified human samples needed to measure Criterion 1 and the
verified-human side of Criterion 2. That evidence is necessary to evaluate
whether any more aggressive AI boundary unfairly labels human writing.
Separately, MF03 is the clearest next validation issue to investigate: define
and test how the route should treat text dominated by control characters.
I stopped without changing it because this milestone allowed exactly one
production change, and combining a validation fix with the threshold
experiment would make the before/after result ambiguous. I would also collect
paired signal-level evidence for EV01–EV09 before choosing a detector change;
the attack names alone do not prove their proposed mechanisms.

**The trade I'd make if this ran for real:** I would keep an appeal path and
favor an inconclusive result over an unsupported authorship accusation.
Lowering the cutoff can catch borderline AI-like outputs such as EV10, but
human writers bear the cost if their work is pushed into the AI-labeled band;
that trade cannot be judged adequately until Criterion 1 has verified data.



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

       [x] Rate limiting on /submit, with your numbers justified
       [x] The pasted run of status codes showing 429
       [x] Audit log with all nine fields, recording rejections too
       [x] The attack set run IN FULL, every input with an outcome
       [x] Ten audit log entries pasted as text
       [x] Five criteria across three trials
       [x] A diagnosis for every miss and every broken attack — stage AND mechanism
       [x] One improvement, with Attack Run — After
       [x] What's Still Broken, including the production trade
       [x] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**

## Capstone

**What This Extends**

This capstone extends Provenance Guard, the existing Flask service that classifies submitted text using GPT-2 and stylometry. It adds operational visibility through per-request latency measurements, structured request outcomes, and error visibility while retaining the existing classification and audit functionality.

**The Shape**

Shape A — Deploy and Instrument, using Path B — Local With Logs, as permitted by the CodePath rubric. The work instruments the existing local service and its logs; it does not replace or retrain GPT-2, change detector signals, weights, or thresholds, add authorship labels or major endpoints, provide public hosting, or rewrite the application.

**Running It**

On Windows, use Python 3.13 and the local PowerShell setup in
[`RUNNING.md`](RUNNING.md). From the repository root, the measured server
command after environment setup is:

```powershell
python -u app.py
```

The measured run used `HOST=127.0.0.1`, `PORT=5000`, `AI201_DEBUG=0`,
`AI201_DETECTOR_MODEL=gpt2`, and `AI201_RATE_LIMITS=1`. Stop the local server
with Ctrl+C in its PowerShell terminal. Python is 3.13; direct dependency
version ranges and setup commands are in [`RUNNING.md`](RUNNING.md). No public
host or credentials are required.

**Instrumentation**

Completed HTTP requests append one JSON object per line to
`logs/operations.jsonl`, separate from the classification and appeal audit in
`logs/audit.jsonl`. Each record has `timestamp`, `request_started_at`,
`request_completed_at`, `duration_ms`, `method`, `endpoint`, `status_code`,
`outcome`, `content_id`, and `error_code`. After the improvement, new records
also include the server-generated `request_id`, returned in `X-Request-Id`.
The historical excerpts below predate that field. Outcomes are `success` (status
below 400), `rejected` (4xx), or `error` (5xx). Content IDs are included only
when a valid UUID is available. Operational records do not include request
bodies, writing, creator IDs, or exception messages. Timestamps are UTC;
duration uses a monotonic clock and includes synchronous classification and
audit writing, but is measured before appending the operational record. It
does not include network transit. `X-Request-Duration-Ms` exposes the same
server-side duration.

The following are actual JSONL events from the local Flask run. The first is a
real rejected HTTP 400 request, the second is the separately timed first
classification while GPT-2 loaded, and the remaining ten are the warm
classification requests used for the timing table below:

```json
{"timestamp":"2026-11-12T00:55:46.104806+00:00","request_started_at":"2026-11-12T00:55:46.103563+00:00","request_completed_at":"2026-11-12T00:55:46.104806+00:00","duration_ms":1.235,"method":"POST","endpoint":"/submit","status_code":400,"outcome":"rejected","content_id":null,"error_code":"invalid_request"}
{"timestamp":"2026-11-12T00:55:56.668712+00:00","request_started_at":"2026-11-12T00:55:46.132073+00:00","request_completed_at":"2026-11-12T00:55:56.668712+00:00","duration_ms":10536.62,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"9bbf2367-0d9f-422f-a9c6-189815b8a4cc","error_code":null}
{"timestamp":"2026-11-12T00:55:56.737626+00:00","request_started_at":"2026-11-12T00:55:56.673567+00:00","request_completed_at":"2026-11-12T00:55:56.737626+00:00","duration_ms":64.059,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"2805a9d3-be93-4f75-8dbb-e158d525dc97","error_code":null}
{"timestamp":"2026-11-12T00:55:57.256807+00:00","request_started_at":"2026-11-12T00:55:57.110403+00:00","request_completed_at":"2026-11-12T00:55:57.256807+00:00","duration_ms":146.382,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"520c3491-264a-4b42-96dd-4bb6e05dfb2e","error_code":null}
{"timestamp":"2026-11-12T00:55:57.788286+00:00","request_started_at":"2026-11-12T00:55:57.626338+00:00","request_completed_at":"2026-11-12T00:55:57.788286+00:00","duration_ms":161.93,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"6d47b445-ee4c-4588-804d-0c40ddf99c39","error_code":null}
{"timestamp":"2026-11-12T00:55:58.324962+00:00","request_started_at":"2026-11-12T00:55:58.163896+00:00","request_completed_at":"2026-11-12T00:55:58.324962+00:00","duration_ms":160.998,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"875797d3-8543-4259-8c27-dc80883c15f5","error_code":null}
{"timestamp":"2026-11-12T00:55:58.837230+00:00","request_started_at":"2026-11-12T00:55:58.683192+00:00","request_completed_at":"2026-11-12T00:55:58.837230+00:00","duration_ms":153.996,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"e3091cfb-6e65-4013-a35f-ca55624231b9","error_code":null}
{"timestamp":"2026-11-12T00:55:59.377363+00:00","request_started_at":"2026-11-12T00:55:59.207736+00:00","request_completed_at":"2026-11-12T00:55:59.377363+00:00","duration_ms":169.613,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"efb52f7d-cf68-4352-a3a6-fd7a324b6e8b","error_code":null}
{"timestamp":"2026-11-12T00:55:59.895103+00:00","request_started_at":"2026-11-12T00:55:59.734432+00:00","request_completed_at":"2026-11-12T00:55:59.895103+00:00","duration_ms":160.653,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"c94247f2-b247-4e24-b34d-ce79ab0f357c","error_code":null}
{"timestamp":"2026-11-12T00:56:00.422424+00:00","request_started_at":"2026-11-12T00:56:00.270004+00:00","request_completed_at":"2026-11-12T00:56:00.422424+00:00","duration_ms":152.406,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"6e7307d4-c401-4004-8dfd-bf29f56db986","error_code":null}
{"timestamp":"2026-11-12T00:56:00.979345+00:00","request_started_at":"2026-11-12T00:56:00.802232+00:00","request_completed_at":"2026-11-12T00:56:00.979345+00:00","duration_ms":177.09,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"fa54340d-b2ac-4d1f-9c37-51a1acea8e14","error_code":null}
{"timestamp":"2026-11-12T00:56:01.505426+00:00","request_started_at":"2026-11-12T00:56:01.345922+00:00","request_completed_at":"2026-11-12T00:56:01.505426+00:00","duration_ms":159.472,"method":"POST","endpoint":"/submit","status_code":200,"outcome":"success","content_id":"e1860599-6bb2-4c8e-8e61-3edb6bff1ca2","error_code":null}
```

**What It Costs**

I measured ten warm `POST /submit` requests from a local client with
`time.perf_counter()` around each HTTP request. Each request used a distinct
test `creator_id` to avoid rate limiting. Client latency is end-to-end for the
local HTTP request. The server measurement is the monotonic `duration_ms`
recorded by Flask from `before_request` through `after_request`; compute-time
per classification is calculated as that duration divided by 1,000. It
includes model inference, stylometry, scoring, existing audit writing, and
response construction. It is not a standalone timing of GPT-2 alone.

| Warm request | Client end-to-end (seconds) | Server processing / classification (seconds) |
|---:|---:|---:|
| 1 | 0.067939 | 0.064059 |
| 2 | 0.168835 | 0.146382 |
| 3 | 0.181009 | 0.161930 |
| 4 | 0.185896 | 0.160998 |
| 5 | 0.161652 | 0.153996 |
| 6 | 0.189810 | 0.169613 |
| 7 | 0.167668 | 0.160653 |
| 8 | 0.176599 | 0.152406 |
| 9 | 0.206883 | 0.177090 |
| 10 | 0.174882 | 0.159472 |
| **Mean** | **0.168117** | **0.150660** |

The first classification was measured separately because it loaded the model:
10.564066 seconds end-to-end and 10.536620 seconds in Flask server processing.
It is not included in the warm means. The GPT-2 cache was already present, so
this first request measured local model loading, not a fresh download. These
are measurements from one local Windows machine and one short sample, not a
benchmark guarantee. They vary with hardware, model/cache state, input length,
system load, and network stack. The measured Flask interval excludes network
transit and operational-log append time, while the client interval includes
local HTTP overhead.

For **100 people per day**, assuming one classification per person and warm
requests comparable to the measured sample, the arithmetic is
`100 x 1 x 0.150660 = 15.066` seconds of aggregate server processing per day.
At five classifications per person, it is
`100 x 5 x 0.150660 = 75.330` seconds per day. These are projections from the
measured mean, not a load test or a measurement of CPU-seconds, electricity,
hosting charges, or dollar cost. They exclude model loading, idle time,
concurrency and queueing effects, and the operational-log append.

**Cost measured on the capstone fixture mix**

The historical Milestone 3 mean above used its own short sample. For the broader
100-to-4,500-character fixture mix in this evaluation, the mean warm server
processing time across 30 requests was **0.889280s before** and
**0.788828s after**. The same timer and exclusions apply. At one comparable
warm request per person, 100 people per day projects to
`100 x 1 x 0.788828 = 78.882800` seconds of aggregate server processing.
At five requests per person, the projection is
`100 x 5 x 0.788828 = 394.414000` seconds per day. These arithmetic
projections use the measured mean; they are not throughput, CPU-time, hosting
price, energy-cost or concurrent-load measurements. Cold model loads are
recorded separately and excluded from both warm means.

**Run Log and Verdicts**

The following is the actual Unit 9 baseline, separate from the earlier
Milestone 3 demonstration and all Unit 8 results. The accepted AI-assisted
criteria were committed as `f973346` before these runs. That commit order
does not establish the unaided authorship required by Milestone 4.

Baseline source commit: `7b6efde65ed4f80f35e9c245a88dab0805b1feb3`.
Criteria SHA-256: `1c9dabee628700159d8fb21d14bcbe63ba2c28aa6d60f1e41c7f12243fcc04e4`.

Reproduction: use the existing Python environment and a clean clone of the
baseline source, then run the committed evaluator:

```powershell
python run_capstone_eval.py --source <clean-checkout> --output <new-evidence-folder> --phase before --port 5001
```

The evaluator starts `python -u app.py` with the documented `PORT=5001`
override because another service occupied port 5000. It does not stop that
existing service. Each trial starts a new process; the process is stopped
after that trial. The existing Python 3.13 environment and cached GPT-2
model are reused. Offline model flags prevent downloads. The runner
terminates only its own process; manual Ctrl+C and fresh dependency
installation are not tested. One startup per trial gives three attempts total.

Each trial uses the same ten synthetic texts of 100, 200, 300, 500, 750,
1,000, 1,500, 2,000, 3,000 and 4,500 characters after a separate warm-up.
The 4,500-character case is valid; the existing detector truncates inputs
to 400 tokens. The texts are generated operational fixtures, not verified
human writing and not an authorship-accuracy dataset. Each successful
request has a distinct creator ID to avoid accidental rate limiting.
Invalid cases must return their expected 400/413 status, so a 429 cannot
substitute for the intended validation path. No code changes occur between trials.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Successful submissions logged | 10/10 each trial | 10/10 | 10/10 | 10/10 | MET |
| 2. Warm server processing time | 10/10 at or below 0.5s | 3/10; max 1.896298s | 4/10; max 1.741125s | 3/10; max 1.701852s | MISSED |
| 3. Operational log privacy | 0 raw-text leaks in 10 cases | 0 leaks; 10/10 observed | 0 leaks; 10/10 observed | 0 leaks; 10/10 observed | MET |
| 4. Invalid requests rejected and logged | 10/10 each trial | 10/10 | 10/10 | 10/10 | MET |
| 5. Documented startup | 3/3 attempts across three trials | 1/1 | 1/1 | 1/1 | MET |

All three trials missed Criterion 2. In total, 20 of 30 warm requests
exceeded 0.5 seconds. The other four criteria met their tested targets.
These finite cases do not prove privacy or latency for every possible input.

**Actual baseline output and producing functions**

Full machine-readable responses, payloads, server output and log excerpts
are preserved in [`results/capstone/`](results/capstone/).

Criterion 1 — `app.py::submit` returns the content ID;
`app.py::_finish_request_timing` and `operational.py::log_request_event`
produce the matching event. Actual trial-1 example:

```json
{
  "response": {
    "status": 200,
    "body": {
      "combined_score": 0.2388,
      "confidence": 0.5224,
      "content_id": "2bb2f1da-80f7-4ed6-947d-01e0dce59428",
      "guess": "human",
      "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
      "model_score": 0.0432,
      "stage": "signals_combined_and_labeled",
      "style_score": 0.4344
    },
    "duration_header_ms": "232.066",
    "request_id_header": null,
    "client_seconds": 0.23836710001341999
  },
  "operational_event": {
    "timestamp": "2026-11-12T13:37:56.956935+00:00",
    "request_started_at": "2026-11-12T13:37:56.724858+00:00",
    "request_completed_at": "2026-11-12T13:37:56.956935+00:00",
    "duration_ms": 232.066,
    "method": "POST",
    "endpoint": "/submit",
    "status_code": 200,
    "outcome": "success",
    "content_id": "2bb2f1da-80f7-4ed6-947d-01e0dce59428",
    "error_code": null
  }
}
```

Criterion 2 — actual server durations from
`app.py::_finish_request_timing`, collected by
`run_capstone_eval.py::run_trial`. Values are milliseconds:

```json
{
  "trial_1": [
    232.066,
    249.485,
    345.952,
    543.876,
    749.726,
    781.134,
    1310.842,
    1614.412,
    1750.692,
    1896.298
  ],
  "trial_2": [
    168.736,
    183.091,
    286.378,
    486.818,
    531.162,
    599.961,
    1236.772,
    1587.231,
    1516.596,
    1741.125
  ],
  "trial_3": [
    164.142,
    188.533,
    301.667,
    572.44,
    694.1,
    746.846,
    1307.553,
    1502.427,
    1686.489,
    1701.852
  ]
}
```

Criterion 3 — actual ten trial-1 privacy events, produced by the same
operational logger. They cover five successes, three missing-creator
rejections and two overlong-text rejections. `privacy_leaks` inspects
field names and string values for the full text, markers and sampled
excerpts; an unexpected schema field also fails the check.

```jsonl
{"timestamp": "2026-11-12T13:38:06.803074+00:00", "request_started_at": "2026-11-12T13:38:06.482205+00:00", "request_completed_at": "2026-11-12T13:38:06.803074+00:00", "duration_ms": 320.865, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "7b7d3112-c116-4845-b88f-849622e16664", "error_code": null}
{"timestamp": "2026-11-12T13:38:07.319818+00:00", "request_started_at": "2026-11-12T13:38:06.858521+00:00", "request_completed_at": "2026-11-12T13:38:07.319818+00:00", "duration_ms": 461.217, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "50af576a-8ab3-468f-a9e9-cbaf4f457de8", "error_code": null}
{"timestamp": "2026-11-12T13:38:07.843847+00:00", "request_started_at": "2026-11-12T13:38:07.360971+00:00", "request_completed_at": "2026-11-12T13:38:07.843847+00:00", "duration_ms": 482.866, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "652d0a48-bbde-4efc-b12d-bab2c635c7b8", "error_code": null}
{"timestamp": "2026-11-12T13:38:08.309000+00:00", "request_started_at": "2026-11-12T13:38:07.868825+00:00", "request_completed_at": "2026-11-12T13:38:08.309000+00:00", "duration_ms": 440.176, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "37332d01-e8f1-46da-909f-2f213fc85b84", "error_code": null}
{"timestamp": "2026-11-12T13:38:08.972685+00:00", "request_started_at": "2026-11-12T13:38:08.334053+00:00", "request_completed_at": "2026-11-12T13:38:08.972685+00:00", "duration_ms": 638.603, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "c75e1dd3-68a3-49ef-859a-53b18a639547", "error_code": null}
{"timestamp": "2026-11-12T13:38:09.005190+00:00", "request_started_at": "2026-11-12T13:38:08.998991+00:00", "request_completed_at": "2026-11-12T13:38:09.005190+00:00", "duration_ms": 6.195, "method": "POST", "endpoint": "/submit", "status_code": 400, "outcome": "rejected", "content_id": null, "error_code": "invalid_request"}
{"timestamp": "2026-11-12T13:38:09.034002+00:00", "request_started_at": "2026-11-12T13:38:09.031374+00:00", "request_completed_at": "2026-11-12T13:38:09.034002+00:00", "duration_ms": 2.611, "method": "POST", "endpoint": "/submit", "status_code": 400, "outcome": "rejected", "content_id": null, "error_code": "invalid_request"}
{"timestamp": "2026-11-12T13:38:09.063749+00:00", "request_started_at": "2026-11-12T13:38:09.061093+00:00", "request_completed_at": "2026-11-12T13:38:09.063749+00:00", "duration_ms": 2.641, "method": "POST", "endpoint": "/submit", "status_code": 400, "outcome": "rejected", "content_id": null, "error_code": "invalid_request"}
{"timestamp": "2026-11-12T13:38:09.108382+00:00", "request_started_at": "2026-11-12T13:38:09.102755+00:00", "request_completed_at": "2026-11-12T13:38:09.108382+00:00", "duration_ms": 5.617, "method": "POST", "endpoint": "/submit", "status_code": 413, "outcome": "rejected", "content_id": null, "error_code": "text_too_long"}
{"timestamp": "2026-11-12T13:38:09.156929+00:00", "request_started_at": "2026-11-12T13:38:09.150914+00:00", "request_completed_at": "2026-11-12T13:38:09.156929+00:00", "duration_ms": 6.007, "method": "POST", "endpoint": "/submit", "status_code": 413, "outcome": "rejected", "content_id": null, "error_code": "text_too_long"}
```

Actual trial-1 privacy check output:

```json
{
  "leaks": [],
  "observed_all_10": true,
  "met": true
}
```

Criterion 4 — `app.py::submit` rejects the malformed request and the
operational logger records the rejection. `run_trial` checks the exact
expected validation status as well as the matching event. Actual example:

```json
{
  "case": "overlong_text",
  "response": {
    "status": 413,
    "body": {
      "error": "text_too_long",
      "message": "'text' must not exceed 5000 characters."
    },
    "duration_header_ms": "3.030",
    "request_id_header": null,
    "client_seconds": 0.011189299984835088
  },
  "operational_event": {
    "timestamp": "2026-11-12T13:38:09.570372+00:00",
    "request_started_at": "2026-11-12T13:38:09.567353+00:00",
    "request_completed_at": "2026-11-12T13:38:09.570372+00:00",
    "duration_ms": 3.03,
    "method": "POST",
    "endpoint": "/submit",
    "status_code": 413,
    "outcome": "rejected",
    "content_id": null,
    "error_code": "text_too_long"
  }
}
```

Criterion 5 — `app.py::main` launches the service; `app.py::health`
produces the response. Actual health responses for the three startups:

```json
{
  "trial_1": {
    "status": 200,
    "body": {
      "detector_loaded": false,
      "detector_model": "gpt2",
      "log_entries": 540,
      "ok": true,
      "rate_limiting": true
    },
    "duration_header_ms": "33.546",
    "request_id_header": null,
    "client_seconds": 2.2042760000331327
  },
  "trial_2": {
    "status": 200,
    "body": {
      "detector_loaded": false,
      "detector_model": "gpt2",
      "log_entries": 571,
      "ok": true,
      "rate_limiting": true
    },
    "duration_header_ms": "23.856",
    "request_id_header": null,
    "client_seconds": 2.05912599992007
  },
  "trial_3": {
    "status": 200,
    "body": {
      "detector_loaded": false,
      "detector_model": "gpt2",
      "log_entries": 602,
      "ok": true,
      "rate_limiting": true
    },
    "duration_header_ms": "50.889",
    "request_id_header": null,
    "client_seconds": 2.0901904000202194
  }
}
```

**Baseline diagnosis**

The missed stage is synchronous classification in `app.py::submit`,
specifically `detector.py::perplexity`, which tokenizes the input and runs
GPT-2 before returning. In all three trials the longer test inputs took
more time than the shortest inputs, up to the configured token cap.
The target was broader than the earlier short-text timing sample.
The maximum baseline duration was 1.896298 seconds; the 0.5-second limit
is retained rather than lowered.

The server timer covers classification and audit writing together. A separate
model-only diagnostic reproduced the slow long-input processing without Flask
or log writes. Each cell below averages three direct calls after warm-up:

| CPU intra-op threads | 300-character model-stage mean (s) | 4,500-character model-stage mean (s) |
|---:|---:|---:|
| 10 | 0.350004 | 1.801996 |
| 1 | 0.395934 | 2.609933 |
| 4 | 0.291058 | 1.865071 |

Full diagnostic output is in
[`thread-diagnostic.json`](results/capstone/thread-diagnostic.json). The tested
thread limits did not improve the long-input mean; no thread setting was changed
in the application. The model scores were identical in these diagnostic calls.
These small, sequential experiments are evidence about this machine, not a
universal thread-count recommendation. PyTorch documents the controls in its
[threading environment-variable reference](https://docs.pytorch.org/docs/stable/threading_environment_variables.html).

There is also a tracing limitation: all 45 rejected baseline requests had no
shared request ID between the HTTP response and operational record. The
acceptance tests can match their events only because requests are serialized
and log boundaries are controlled. That does not provide robust correlation
when unrelated traffic interleaves. The existing logging criteria were too
limited to expose this as an acceptance miss; the separate correlation
diagnostic records it explicitly.

**The Improvement**

One operational change adds a server-generated UUID for every request.
`app.py::_start_request_timing` creates it; `_finish_request_timing` writes it
as `request_id` and returns the same value in `X-Request-Id`. It covers success,
validation rejection, rate limiting, and handled server-error responses.
Incoming client IDs are ignored, so arbitrary client text cannot enter the
operational log through this field. This addresses the measured tracing gap,
not the unresolved model-compute latency miss.

No model weights, detector code, scoring formula, thresholds, token limit,
classification response body, or acceptance target is changed. Existing
records without request IDs are preserved. UUID generation occurs before the existing server timer starts, and the
operational-log append remains outside that timer. Preserved client timings
include the full local HTTP interval. The change adds a small UUID and
log-field overhead; the full acceptance suite was rerun below to measure the
result rather than assume it is free.

Eight focused regression tests passed, including valid/invalid correlation,
unique IDs, rejection of client-supplied IDs, privacy, rate limiting, server
errors, and existing route behavior. The server-error test deliberately emits
a traceback and still passes; that is injected test traffic, not a live crash.



**Measured before/after results**

Improvement source commit: `8da495c475c587de51b4375a007771dd20230564`.
The same evaluator, criteria, synthetic input texts, three fresh server
processes, cached model and reused environment were used. No acceptance
target was revised. Full after-change evidence is under
[`results/capstone/`](results/capstone/).

| Criterion | Unchanged target | Before 1 | Before 2 | Before 3 | After 1 | After 2 | After 3 | Before / After verdict |
|---|---|---|---|---|---|---|---|---|
| 1. Successful submissions logged | 10/10 each trial | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | MET / MET |
| 2. Warm processing time | All 10 at or below 0.5s | 3/10; max 1.896298s | 4/10; max 1.741125s | 3/10; max 1.701852s | 4/10; max 1.513196s | 4/10; max 1.425065s | 3/10; max 1.793009s | MISSED / MISSED |
| 3. Operational privacy | 0 raw-text leaks | 0 detected leaks | 0 detected leaks | 0 detected leaks | 0 detected leaks | 0 detected leaks | 0 detected leaks | MET / MET |
| 4. Invalid inputs | 10/10 rejected and logged | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | MET / MET |
| 5. Startup | 3/3 across three trials | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | MET / MET |

| Additional tracing diagnostic (not a new acceptance criterion) | Before | After |
|---|---:|---:|
| Rejected responses with matching request IDs in logs | 0/45 | 45/45 |
| All after-run response/log pairs with matching IDs | — | 99/99 |

The change improved traceability: all 45 rejected after-run requests could
be matched by ID, and all 99 recorded after-run requests had distinct UUIDs.
The 45 paired successful classification responses retained identical
model/style/combined scores, guesses, labels and confidence values.
This directly checks the tested fixtures; it is not a proof about every input.

The mean across the same 30 warm requests was 0.889280s before and
0.788828s after; maxima were 1.896298s and 1.793009s.
The after phase still had 19/30 warm requests above 0.5 seconds.
The correlation change does not optimize model computation. Separate
phases run sequentially on a shared laptop, so changes in latency cannot
be attributed solely to the tiny extra UUID/logging work. The improvement
is demonstrated by direct correlation, not by a claim of faster inference.

**Actual after-change output**

Criteria 1 and 4 — real trial-1 success and rejection, from `submit`,
`_start_request_timing`, `_finish_request_timing` and `log_request_event`:

```json
{
  "successful_submission": {
    "response": {
      "status": 200,
      "body": {
        "combined_score": 0.2388,
        "confidence": 0.5224,
        "content_id": "e831da25-a3ca-4b9e-8a0e-e6fd1e534f23",
        "guess": "human",
        "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
        "model_score": 0.0432,
        "stage": "signals_combined_and_labeled",
        "style_score": 0.4344
      },
      "duration_header_ms": "132.164",
      "request_id_header": "d5d824b1-048a-4457-ac27-430ca7f21f8c",
      "client_seconds": 0.13741480000317097
    },
    "event": {
      "timestamp": "2026-11-12T13:50:04.154043+00:00",
      "request_id": "d5d824b1-048a-4457-ac27-430ca7f21f8c",
      "request_started_at": "2026-11-12T13:50:04.021876+00:00",
      "request_completed_at": "2026-11-12T13:50:04.154043+00:00",
      "duration_ms": 132.164,
      "method": "POST",
      "endpoint": "/submit",
      "status_code": 200,
      "outcome": "success",
      "content_id": "e831da25-a3ca-4b9e-8a0e-e6fd1e534f23",
      "error_code": null
    }
  },
  "invalid_submission": {
    "response": {
      "status": 400,
      "body": {
        "error": "invalid_request",
        "message": "'text' must be a non-empty string."
      },
      "duration_header_ms": "2.679",
      "request_id_header": "34a72288-2e5c-4258-8d89-413d94b05684",
      "client_seconds": 0.013171599945053458
    },
    "event": {
      "timestamp": "2026-11-12T13:50:14.617368+00:00",
      "request_id": "34a72288-2e5c-4258-8d89-413d94b05684",
      "request_started_at": "2026-11-12T13:50:14.614681+00:00",
      "request_completed_at": "2026-11-12T13:50:14.617368+00:00",
      "duration_ms": 2.679,
      "method": "POST",
      "endpoint": "/submit",
      "status_code": 400,
      "outcome": "rejected",
      "content_id": null,
      "error_code": "invalid_request"
    }
  }
}
```

Criterion 2 — actual `_finish_request_timing` durations, milliseconds:

```json
{
  "trial_1": [
    132.164,
    181.173,
    287.246,
    443.693,
    732.719,
    557.288,
    1248.932,
    1372.877,
    1513.196,
    1362.561
  ],
  "trial_2": [
    142.086,
    179.127,
    270.224,
    448.475,
    511.082,
    515.16,
    1054.897,
    1416.989,
    1408.893,
    1425.065
  ],
  "trial_3": [
    217.555,
    242.974,
    312.816,
    527.086,
    601.405,
    716.363,
    1191.8,
    1305.324,
    1552.658,
    1793.009
  ]
}
```

Criterion 3 — actual trial-1 privacy events and evaluator output:

```jsonl
{"timestamp": "2026-11-12T13:50:12.482138+00:00", "request_id": "5644230e-df14-44de-88f2-9e7e19d2a44c", "request_started_at": "2026-11-12T13:50:12.246936+00:00", "request_completed_at": "2026-11-12T13:50:12.482138+00:00", "duration_ms": 235.197, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "8d665b11-804c-4b72-b3ec-5ca42cf2ce3f", "error_code": null}
{"timestamp": "2026-11-12T13:50:12.871737+00:00", "request_id": "a7b95004-2e35-4310-beaa-e53655591fac", "request_started_at": "2026-11-12T13:50:12.545444+00:00", "request_completed_at": "2026-11-12T13:50:12.871737+00:00", "duration_ms": 326.293, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "3265f0f0-547a-4854-af32-23d006d25fb3", "error_code": null}
{"timestamp": "2026-11-12T13:50:13.325094+00:00", "request_id": "42e85bfb-65bd-42b7-b47d-87291b519d0e", "request_started_at": "2026-11-12T13:50:12.895726+00:00", "request_completed_at": "2026-11-12T13:50:13.325094+00:00", "duration_ms": 429.37, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "27a5b2db-574e-4f3a-a4cf-9faf7ceb7a26", "error_code": null}
{"timestamp": "2026-11-12T13:50:13.854122+00:00", "request_id": "15f018e5-5624-4d7d-b14d-4046a03cda0e", "request_started_at": "2026-11-12T13:50:13.367393+00:00", "request_completed_at": "2026-11-12T13:50:13.854122+00:00", "duration_ms": 486.72, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "7f24f1f7-15f8-48f4-8ac5-49c275998546", "error_code": null}
{"timestamp": "2026-11-12T13:50:14.342179+00:00", "request_id": "175df903-81fb-483e-bbf7-411a8bf2e0cf", "request_started_at": "2026-11-12T13:50:13.893877+00:00", "request_completed_at": "2026-11-12T13:50:14.342179+00:00", "duration_ms": 448.288, "method": "POST", "endpoint": "/submit", "status_code": 200, "outcome": "success", "content_id": "7989c36e-751e-4c2b-a766-87e485dd262e", "error_code": null}
{"timestamp": "2026-11-12T13:50:14.390395+00:00", "request_id": "855d8cb9-7f8b-4170-bce4-8570c9de508b", "request_started_at": "2026-11-12T13:50:14.385151+00:00", "request_completed_at": "2026-11-12T13:50:14.390395+00:00", "duration_ms": 5.243, "method": "POST", "endpoint": "/submit", "status_code": 400, "outcome": "rejected", "content_id": null, "error_code": "invalid_request"}
{"timestamp": "2026-11-12T13:50:14.431947+00:00", "request_id": "0278c849-005b-4d5a-b71b-1a5bd2ed1bcd", "request_started_at": "2026-11-12T13:50:14.429272+00:00", "request_completed_at": "2026-11-12T13:50:14.431947+00:00", "duration_ms": 2.672, "method": "POST", "endpoint": "/submit", "status_code": 400, "outcome": "rejected", "content_id": null, "error_code": "invalid_request"}
{"timestamp": "2026-11-12T13:50:14.475790+00:00", "request_id": "ab5efeef-dad0-4b5e-99ed-b534aae32a7b", "request_started_at": "2026-11-12T13:50:14.470992+00:00", "request_completed_at": "2026-11-12T13:50:14.475790+00:00", "duration_ms": 4.782, "method": "POST", "endpoint": "/submit", "status_code": 400, "outcome": "rejected", "content_id": null, "error_code": "invalid_request"}
{"timestamp": "2026-11-12T13:50:14.540721+00:00", "request_id": "b7ec2f61-a642-4feb-b827-b311fe920483", "request_started_at": "2026-11-12T13:50:14.535557+00:00", "request_completed_at": "2026-11-12T13:50:14.540721+00:00", "duration_ms": 5.141, "method": "POST", "endpoint": "/submit", "status_code": 413, "outcome": "rejected", "content_id": null, "error_code": "text_too_long"}
{"timestamp": "2026-11-12T13:50:14.587490+00:00", "request_id": "00dd396d-4c4b-4698-b355-73fe42581c67", "request_started_at": "2026-11-12T13:50:14.583121+00:00", "request_completed_at": "2026-11-12T13:50:14.587490+00:00", "duration_ms": 4.348, "method": "POST", "endpoint": "/submit", "status_code": 413, "outcome": "rejected", "content_id": null, "error_code": "text_too_long"}
```

```json
{
  "leaks": [],
  "observed_all_10": true,
  "met": true
}
```

Criterion 5 — actual `health` responses from the three after-change startups:

```json
{
  "trial_1": {
    "status": 200,
    "body": {
      "detector_loaded": false,
      "detector_model": "gpt2",
      "log_entries": 540,
      "ok": true,
      "rate_limiting": true
    },
    "duration_header_ms": "31.088",
    "request_id_header": "a55707cf-0718-42e3-b2cf-14c777669a4c",
    "client_seconds": 1.7088085000868887
  },
  "trial_2": {
    "status": 200,
    "body": {
      "detector_loaded": false,
      "detector_model": "gpt2",
      "log_entries": 571,
      "ok": true,
      "rate_limiting": true
    },
    "duration_header_ms": "31.956",
    "request_id_header": "e04a378d-0f69-452d-8026-4af133b70149",
    "client_seconds": 1.5630262999329716
  },
  "trial_3": {
    "status": 200,
    "body": {
      "detector_loaded": false,
      "detector_model": "gpt2",
      "log_entries": 602,
      "ok": true,
      "rate_limiting": true
    },
    "duration_header_ms": "29.574",
    "request_id_header": "da96071c-4893-4aba-a82d-9741994eb3a9",
    "client_seconds": 1.5455490000313148
  }
}
```

**What's Still Broken**

Criterion 2 remains MISSED: 19 of 30 warm requests exceeded the
unchanged 0.5-second target. The remaining bottleneck is synchronous
GPT-2 processing for the longer texts, as demonstrated by the separate
model-stage measurements. The two reduced-thread experiments did not
justify changing the runtime. The request-ID improvement deliberately
addresses observability and does not claim to fix that latency miss.

The proposed next step is a dedicated model-stage profile on the same
long-input fixtures under controlled machine load. That is the first
step because the measured model call already accounts for most of the
slow request; guessing at more thread settings or trimming text would
not establish a sound fix. Work stopped after the one measured
operational improvement to preserve the agreed scope and unchanged
scoring behavior. The target was not loosened to turn a miss into a pass.

Other limits remain: startup reused installed packages and cached model
files; package ranges are not a fully locked installation; clean manual
shutdown and a fresh install were not evaluated. Logging-disk failures,
concurrent load, and broader privacy failure modes are outside these
trials. No raw-text leaks were detected in `operations.jsonl` for the
tested inputs; this is not a claim that every application output is private.

The accepted criteria and this write-up include AI-generated wording.
The technical evaluation is complete, but these artifacts do not satisfy
or certify the rubric's separate requirement for unaided student-written
criteria. Instructor review is needed before representing that requirement
as fulfilled. Nothing has been pushed or submitted by this workflow.

**How I Used AI**

1. The student chose the five targets and asked ChatGPT for review, examples,
   and complete wording. ChatGPT drafted the criteria and testing procedures;
   the student accepted an explicitly AI-assisted version for evaluation.
   The privacy plan was narrowed to five valid and five invalid submissions,
   and startup was clarified as one attempt in each of three trials. This
   history is disclosed rather than claimed as unaided student authorship.
2. The student asked Codex to continue the repository work. Codex wrote the
   evaluator and synthetic fixtures, ran and preserved the actual before/after
   trials, diagnosed latency, tested two CPU-thread alternatives, and rejected
   those alternatives when they did not improve the long-input mean. The
   single implemented change adds server-generated request IDs. Codex also
   generated these evidence tables, cost arithmetic and proposed next steps
   from the saved outputs; the student must review and be able to explain them.

Verification: eight focused operational tests and nine environment checks
passed. The environment check's one ping event was redirected to an isolated
temporary log. All original Unit 7/8 source scoring and logs were preserved.
The criteria and evaluator hashes match between phases; complete validation
is in [`comparison-validation.json`](results/capstone/comparison-validation.json).
