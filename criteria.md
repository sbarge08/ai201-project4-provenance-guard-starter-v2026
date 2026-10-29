# Acceptance criteria — Provenance Guard

These are the targets I will evaluate in Unit 8, not results from testing.
The evaluation datasets have not yet been collected or verified.

The combined score is an AI-likeness evidence score from 0 to 1. A higher
score means stronger AI-like evidence; it is not a calibrated probability
that AI authored the text and does not prove authorship.

## 1. False-positive rate — At most 1 out of 20 (5%)

**Target:** Of 20 verified human-written texts, at most one may receive the
high-confidence AI label in each of three trials.

**How I will test it:** Use the same fixed set of 20 verified human-written
texts across all three trials. Submit each text, record the returned guess,
and count high-confidence AI classifications. Each trial must meet the target.

**Why I chose this target:** Falsely accusing someone of using AI can be more
damaging than missing AI-generated writing. The system should be cautious when
evidence is uncertain. Even 5% is a meaningful risk, so this is a preliminary
benchmark rather than proof the system is safe.

## 2. Score separation — At least 0.20

**Target:** The average combined AI-likeness score for 20 known AI-generated
texts must exceed the average for 20 verified human-written texts by at least
0.20 in each of three trials.

**How I will test it:** Use the same fixed, labeled set of 40 texts across all
three trials. Calculate the mean combined AI-likeness score separately for
human and AI examples, then subtract the human mean from the AI mean. Use the
combined score, not classification confidence.

**Why I chose this target:** If both groups receive similar scores, the
detector is not distinguishing them effectively. A 0.20 gap represents
noticeable separation, although the score does not prove authorship.

## 3. Label coverage — All three labels

**Target:** All three labels (`ai`, `human`, `unsure`) must be reachable, and
every combined score from 0 through 1 must map to exactly one label.

**How I will test it:** Directly test `scoring.score_to_label` with
representative values inside all three ranges, the exact thresholds, values
immediately below and above each threshold, and the endpoints 0 and 1. Verify
complete, nonoverlapping score ranges.

**Why I chose this target:** The unsure category is essential when evidence is
inconclusive. Every score must produce a consistent result instead of forcing
an unsupported accusation.

## 4. Appeal reliability — 100% of 10 valid appeals

**Target:** All 10 valid appeals in each of three trials must be recorded and
move their corresponding submission to `under_review`.

**How I will test it:** Create 10 valid submissions, capture their
`content_id` values, and submit an appeal for each using its real ID and
nonempty written reasoning. Verify the audit log contains each appeal, its
reasoning, and the `under_review` status. Repeat with new submissions across
three trials. The appeal entry must use the submission's `content_id`; the
original decision remains in the append-only log.

**Why I chose this target:** Writers need a reliable way to challenge
incorrect decisions. A valid appeal should never disappear or leave the
submission's status unchanged.

## 5. Invalid-input handling — 100% of six cases

**Target:** All six predefined invalid requests must receive an appropriate
HTTP 4xx response and must not create a valid decision record, in every one of
three trials.

**How I will test it:** Test these six requests: missing `text`, empty `text`,
whitespace-only `text`, non-string `text`, missing `creator_id`, and `text`
exceeding 5,000 characters (5,001 or more). Check the HTTP response and audit
log for each case. A rejection entry may be logged, but no valid decision
record may be created.

**Why I chose this target:** A public-facing service must reject invalid input
consistently without crashing or creating unreliable audit decisions.

## Unit 8 evaluation note

Keep these targets unchanged during evaluation. Report misses against the
selected targets rather than lowering them. Revise a criterion only if it
proves unmeasurable, and preserve the original wording when documenting any
revision.
