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

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

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
