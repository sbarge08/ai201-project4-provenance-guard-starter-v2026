# Provenance Guard: System Design

## Submission flow

`POST /submit` is not implemented yet. The intended flow is:

1. Receive a JSON object with the required `text` and `creator_id` fields.
2. Validate that the body is a JSON object and that both required values are
   non-empty strings. Reject invalid input instead of trying to score it.
3. Generate a unique `content_id` for this submission. Return it to the writer
   so it can be used to appeal this decision.
4. Send the text to the local GPT-2 detector. It estimates how predictable the
   text is and returns a model score.
5. Measure the text's style with the separate stylometry signal.
6. Combine the two 0–1 scores. A higher combined score means stronger
   AI-like evidence; it is not a calibrated probability that AI wrote the text.
7. Map the combined score to a human, unsure, or AI guess and a
   reader-facing sentence. An unsure result should communicate uncertainty,
   not imply wrongdoing.
8. Append the decision to the audit log, including the content and creator
   IDs, both signal scores, combined score, guess, label, timestamp, and
   `decided` status.
9. Return the decision and its signal scores as JSON to the writer.

The order matters: validation happens before scoring, and the decision is
logged before a successful response is returned. A model score alone is never
proof of authorship.

## Signals

### GPT-2 perplexity-based signal

The detector measures how surprised GPT-2 is by the words in a text.
Perplexity is lower when the text is more predictable. The starter converts
that into a 0–1 model score where a higher value means more AI-like evidence.
It runs locally and truncates the text at the configured 400-token limit.

Predictability does not establish who wrote something. Plain, conventional
sentences and common vocabulary can be predictable whether written by a person
or a model. This can unfairly affect writers who use simpler language,
including younger writers and people writing in a second language. Unusual or
ornate prose can instead be less predictable and appear more human-like to
this signal. Topic and text length also affect the reading.

### Stylometry

Stylometry measures text form, not meaning:

- **Sentence-length variation** measures whether sentences are similar in
  length or vary more.
- **Vocabulary diversity** measures how much the words repeat, using unique
  words relative to total words.
- **Punctuation density** measures how much punctuation appears relative to
  the text's length.

These features may describe patterns often associated with generated or human
writing, but they do not prove authorship. Stylometry cannot understand the
text's meaning or distinguish the original author. Typos, sentence splitting,
quotations, and other surface edits can change its measurements without
changing the ideas. Vocabulary diversity also depends on text length.

## False-positive scenario and appeal

A person writes a short, plain explanation in familiar words. GPT-2 finds it
predictable, and its simple, evenly sized sentences may also look regular to
stylometry. The combined evidence crosses the AI threshold, so the writer sees
a high-confidence AI label despite having written the text themselves.

That false accusation can damage trust and unfairly affect how the writer's
work is treated. The result should therefore be presented as an estimate, not
proof. Show the label and plain-language explanation, the combined
AI-likeness score, and the separate model and style scores. Explain that
predictability and writing style can produce false positives. Do not expose
other writers' submissions, scores, or appeal details.

Every writer must be able to appeal. The result supplies a `content_id`; the
writer sends that ID and their reasoning to `POST /appeal`. The service checks
that the submission exists and that the caller is allowed to appeal it, then
records the appeal as `under_review`. The appeal response should confirm that
it was recorded without revealing private information about any other writer.

## API structures

The starter documents the request fields below. It does not specify maximum
lengths, optional request fields, error-response shapes, or an exact success
response for appeals. The routes currently return `501 not_implemented`.

### `POST /submit`

Required request fields, as documented in `app.py`:

```json
{
  "text": "The writing to review.",
  "creator_id": "writer-123"
}
```

No optional request fields are specified in the starter. The response is
documented to include at least these fields:

```json
{
  "content_id": "generated-id",
  "guess": "unsure",
  "confidence": 0.52,
  "label": "We cannot tell from these signals whether this was written by a person or AI.",
  "model_score": 0.61,
  "style_score": 0.43
}
```

The response fields shown above are the starter's documented minimum. The
starter does not define the exact wording of labels or how `confidence` is
calculated. For this design, `confidence` should be understood as the
combined AI-like evidence score, not a probability of AI authorship. The
separate scores should also be returned so the writer can see what informed
the result. `combined_score` may be included as an additional response field,
but is not part of the documented minimum.

### `POST /appeal`

Required request fields, as documented in `app.py`:

```json
{
  "content_id": "generated-id",
  "reasoning": "I wrote this text myself and would like the decision reviewed."
}
```

No optional request fields are specified in the starter. The documented
appeal flow does not ask the caller to send `creator_id`; the service should
associate the appeal with the original submission using `content_id` and
verify that the caller is entitled to appeal it.

The starter requires confirmation to the writer but does not define a success
response shape. A minimal proposed response is:

```json
{
  "content_id": "generated-id",
  "status": "under_review"
}
```

Here, `content_id` and `status` are proposed confirmation fields, not fields
whose exact response shape is specified by the starter. No optional appeal
response fields are required by the starter.

## Audit log and appeals

The audit log is an append-only JSON Lines file at `logs/audit.jsonl`.
`audit.log_decision(...)` records a timestamp, `content_id`, `creator_id`,
guess, model score, style score, combined score, label, and status. This keeps
a trace of what the service decided and which scores informed the result.

`audit.log_appeal(content_id, creator_id, reasoning)` appends a separate
appeal entry with the same `content_id`, an appeal event, a timestamp, the
reasoning, and `under_review` status. It does not replace or edit the original
decision. The shared content ID connects the appeal to that decision and
preserves the order of events. Only an authorized writer should be able to
submit an appeal, and API responses must not expose another writer's private
log entries or reasoning.
