# Attack run — after

- Produced by: `run_attacks.py::main`
- Service: `app.py::submit`
- 56 attacks · 2026-11-04 20:41
- Auto-marked BROKE (5xx, crash, no response): **0**
- Left for you to judge: **56**

The Verdict column is blank where a script can't honestly decide. Whether
an evasion worked depends on where you put your thresholds — read the
`targets` column, look at what came back, and write HELD or BROKE yourself.

Each attack submits as creator_id `attacker_<id>`, and the content_id it
came back with is in the table — either one will match this run against your
audit log when you go looking for the ten entries to paste.

| ID | Family | Targeting | Status | Content ID | Guess | Score | Verdict |
|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | `deb57601-bcb1-45bc-8ce7-e2fea1b61f3f` | unsure | 0.555 |  |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | `7578d3c3-4787-4f9b-bbbe-00c6465b6926` | unsure | 0.934 |  |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | `b63af6bc-8626-42c3-9a8c-f82e8dd0b141` | unsure | 0.938 |  |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | `24fb6bfe-6f2b-49e2-862e-275f03add19b` | unsure | 0.977 |  |
| EV05 | evasion | both signals: heavy human editing pass | 200 | `9eaa99ab-3014-4a3e-9a26-381074bbd0e2` | unsure | 0.714 |  |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | `ae85c5d8-9ecc-4d8b-9d8f-f9e208573f20` | unsure | 0.873 |  |
| EV07 | evasion | signal two: padding with punctuation | 200 | `060da6a3-2507-47e7-b137-93bd2f254049` | unsure | 0.949 |  |
| EV08 | evasion | signal one: text below the token window | 200 | `0a30fa7f-461c-49e8-b3cb-302243632dfe` | unsure | 0.631 |  |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | `39e84cf1-81c6-499e-8ed5-7ac56a4ab765` | unsure | 0.911 |  |
| EV10 | evasion | signal two: repeated stanza structure | 200 | `8a5c44f9-7cd0-4c1e-adb0-a52fcc37fe6e` | ai | 0.512 |  |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | `2d0dcd6c-d59f-4a25-b7da-d73ceda286f7` | unsure | 0.967 |  |
| FP02 | false_positive | human writing in a formal register | 200 | `88cdfe7a-a514-4b57-9bef-0385a6cac80d` | unsure | 0.808 |  |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | `814fec47-cf86-4c0b-8b3e-459c69db0614` | unsure | 0.761 |  |
| FP04 | false_positive | a student essay written to a rubric | 200 | `b64dd67d-7ed5-438e-9052-0f3379139431` | unsure | 0.758 |  |
| FP05 | false_positive | technical documentation written by a person | 200 | `7a933a48-3189-4a94-bc6b-dea32520955b` | unsure | 0.687 |  |
| FP06 | false_positive | a person imitating a formal template | 200 | `12997357-0a53-4e3f-bdff-70645c0e3b6c` | unsure | 0.706 |  |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | `7d42a06c-e2e8-4811-8a60-4380d454cd8e` | unsure | 0.614 |  |
| FP08 | false_positive | very short genuine human submission | 200 | `5c30935a-8532-4db3-9937-2c45833c93db` | unsure | 0.861 |  |
| PI01 | prompt_injection | instruction to ignore the check | 200 | `3143c09e-3157-4d43-8883-2530d867956c` | unsure | 0.755 |  |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | `3ba38da5-2f0c-41cf-92cf-c0db24ec226e` | unsure | 0.511 |  |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | `0c9acbab-e5d9-4222-98b6-97b13429fa68` | unsure | 0.962 |  |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | `0f3a5309-9c62-4884-b5b1-70f9b9d41605` | unsure | 0.945 |  |
| PI05 | prompt_injection | attempt to inject into the audit log | 200 | `e8367556-8dc5-4fb1-b975-f20f7e178117` | unsure | 0.756 |  |
| PI06 | prompt_injection | instruction plus real human text | 200 | `51a63a51-d15d-4c95-8eef-dd650992713b` | unsure | 0.971 |  |
| MF01 | malformed | text is only whitespace | 400 | `—` | — | — |  |
| MF02 | malformed | text is a single character | 422 | `ec7602af-464f-4728-9490-2bb757e678d9` | — | — |  |
| MF03 | malformed | text is control characters | 200 | `9aa7edca-b855-4258-bf83-794473b666b8` | human | 0.516 |  |
| MF04 | malformed | text is only punctuation | 200 | `231e5bcb-1af6-4c16-b134-29bfb0003dd8` | unsure | 0.685 |  |
| MF05 | malformed | text is a very long single word | 200 | `ee30ad1c-9056-4597-925d-8d4fc75b8f66` | unsure | 0.808 |  |
| MF06 | malformed | text is emoji only | 200 | `a9c6225f-9bc4-4346-b30f-853e36551843` | unsure | 0.635 |  |
| MF07 | malformed | text is right-to-left script | 200 | `5c0accca-6b33-4652-b894-0aba210f37ab` | unsure | 0.870 |  |
| MF08 | malformed | text is 60,000 characters | 413 | `—` | — | — |  |
| RQ01 | malformed | no text field at all | 400 | `—` | — | — |  |
| RQ02 | malformed | no creator_id | 400 | `—` | — | — |  |
| RQ03 | malformed | text is a number | 400 | `—` | — | — |  |
| RQ04 | malformed | text is a list | 400 | `—` | — | — |  |
| RQ05 | malformed | text is null | 400 | `—` | — | — |  |
| RQ06 | malformed | creator_id is an object | 400 | `—` | — | — |  |
| RQ07 | malformed | body is a JSON array, not an object | 400 | `—` | — | — |  |
| RQ08 | malformed | body is unparseable JSON | 400 | `—` | — | — |  |
| RQ09 | malformed | body is empty | 400 | `—` | — | — |  |
| RQ10 | malformed | body is form-encoded, not JSON | 400 | `—` | — | — |  |
| RQ11 | malformed | body is JSON claiming to be plain text | 400 | `—` | — | — |  |
| RQ12 | malformed | deeply nested JSON | 400 | `—` | — | — |  |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 200 | `ef38fe85-1b83-4824-96fa-f5e3d35cd3d1` | human | 0.744 |  |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 200 | `71d9bd58-9995-478e-a90c-e45ff4df2b4a` | human | 0.744 |  |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 200 | `3c7aab9a-5929-49a7-b4a4-92f6f2715578` | human | 0.744 |  |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 200 | `65be1052-8476-4c0a-b201-53db70138746` | human | 0.744 |  |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 200 | `26b7289a-3d4e-4bd6-a41c-e84dc282e166` | human | 0.744 |  |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 200 | `7a7f6749-6764-44f2-985e-b8f2c0e9b98c` | human | 0.744 |  |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 200 | `ef7e19b9-56c0-4676-84b7-ef4e8d1a1234` | human | 0.744 |  |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 200 | `141ffd05-effb-4a6b-825c-6f37c3a64e1b` | human | 0.744 |  |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 200 | `612402fb-840c-4e09-a4a1-ef9f6e35dd12` | human | 0.744 |  |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 200 | `cd60bf9f-105b-4791-a5ac-adbdef429b50` | human | 0.744 |  |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |

---

## By family

| Family | Attacks | Auto-BROKE | Left to judge |
|---|---|---|---|
| `evasion` | 10 | 0 | 10 |
| `false_positive` | 8 | 0 | 8 |
| `flood_same_creator` | 12 | 0 | 12 |
| `malformed` | 20 | 0 | 20 |
| `prompt_injection` | 6 | 0 | 6 |

> The **false_positive** family is the one to look at hardest. Those are
> written to be genuine human writing that reads as machine-like. Every one
> your service calls AI is a real writer it would have accused.

---

## What came back

The detail behind the table. Paste the interesting failures into your
README — the ones that show something, not the ten easiest.

### EV01 — `evasion`

*Targeting:* signal two: typos raise word variety

```json
{
  "id": "EV01",
  "status": 200,
  "content_id": "deb57601-bcb1-45bc-8ce7-e2fea1b61f3f",
  "creator_id": "attacker_EV01",
  "guess": "unsure",
  "confidence": 0.5548,
  "model_score": 0.1635,
  "style_score": 0.3891,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV02 — `evasion`

*Targeting:* signal two: broken-up sentences raise length spread

```json
{
  "id": "EV02",
  "status": 200,
  "content_id": "7578d3c3-4787-4f9b-bbbe-00c6465b6926",
  "creator_id": "attacker_EV02",
  "guess": "unsure",
  "confidence": 0.934,
  "model_score": 0.5943,
  "style_score": 0.3222,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV03 — `evasion`

*Targeting:* signal two: a pasted quotation changes the shape

```json
{
  "id": "EV03",
  "status": 200,
  "content_id": "b63af6bc-8626-42c3-9a8c-f82e8dd0b141",
  "creator_id": "attacker_EV03",
  "guess": "unsure",
  "confidence": 0.9375,
  "model_score": 0.6662,
  "style_score": 0.3738,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV04 — `evasion`

*Targeting:* signal one: unusual words raise perplexity

```json
{
  "id": "EV04",
  "status": 200,
  "content_id": "24fb6bfe-6f2b-49e2-862e-275f03add19b",
  "creator_id": "attacker_EV04",
  "guess": "unsure",
  "confidence": 0.9771,
  "model_score": 0.6114,
  "style_score": 0.3905,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV05 — `evasion`

*Targeting:* both signals: heavy human editing pass

```json
{
  "id": "EV05",
  "status": 200,
  "content_id": "9eaa99ab-3014-4a3e-9a26-381074bbd0e2",
  "creator_id": "attacker_EV05",
  "guess": "unsure",
  "confidence": 0.7135,
  "model_score": 0.3212,
  "style_score": 0.3838,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV06 — `evasion`

*Targeting:* signal two: one very long sentence and one very short

```json
{
  "id": "EV06",
  "status": 200,
  "content_id": "ae85c5d8-9ecc-4d8b-9d8f-f9e208573f20",
  "creator_id": "attacker_EV06",
  "guess": "unsure",
  "confidence": 0.8727,
  "model_score": 0.5727,
  "style_score": 0.2851,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV07 — `evasion`

*Targeting:* signal two: padding with punctuation

```json
{
  "id": "EV07",
  "status": 200,
  "content_id": "060da6a3-2507-47e7-b137-93bd2f254049",
  "creator_id": "attacker_EV07",
  "guess": "unsure",
  "confidence": 0.9487,
  "model_score": 0.5862,
  "style_score": 0.3446,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV08 — `evasion`

*Targeting:* signal one: text below the token window

```json
{
  "id": "EV08",
  "status": 200,
  "content_id": "0a30fa7f-461c-49e8-b3cb-302243632dfe",
  "creator_id": "attacker_EV08",
  "guess": "unsure",
  "confidence": 0.6308,
  "model_score": 0.2452,
  "style_score": 0.3803,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV09 — `evasion`

*Targeting:* both: AI text with a human opening paragraph bolted on

```json
{
  "id": "EV09",
  "status": 200,
  "content_id": "39e84cf1-81c6-499e-8ed5-7ac56a4ab765",
  "creator_id": "attacker_EV09",
  "guess": "unsure",
  "confidence": 0.911,
  "model_score": 0.7042,
  "style_score": 0.3611,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### EV10 — `evasion`

*Targeting:* signal two: repeated stanza structure

```json
{
  "id": "EV10",
  "status": 200,
  "content_id": "8a5c44f9-7cd0-4c1e-adb0-a52fcc37fe6e",
  "creator_id": "attacker_EV10",
  "guess": "ai",
  "confidence": 0.5117,
  "model_score": 0.9792,
  "style_score": 0.4934,
  "label": "High-confidence AI-like patterns: this system's signals are strongly associated with AI-generated writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FP01 — `false_positive`

*Targeting:* plain, clear human writing with no flourishes

```json
{
  "id": "FP01",
  "status": 200,
  "content_id": "2d0dcd6c-d59f-4a25-b7da-d73ceda286f7",
  "creator_id": "attacker_FP01",
  "guess": "unsure",
  "confidence": 0.9669,
  "model_score": 0.6175,
  "style_score": 0.3943,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### FP02 — `false_positive`

*Targeting:* human writing in a formal register

```json
{
  "id": "FP02",
  "status": 200,
  "content_id": "88cdfe7a-a514-4b57-9bef-0385a6cac80d",
  "creator_id": "attacker_FP02",
  "guess": "unsure",
  "confidence": 0.8085,
  "model_score": 0.7387,
  "style_score": 0.4251,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### FP03 — `false_positive`

*Targeting:* a non-native English speaker writing carefully

```json
{
  "id": "FP03",
  "status": 200,
  "content_id": "814fec47-cf86-4c0b-8b3e-459c69db0614",
  "creator_id": "attacker_FP03",
  "guess": "unsure",
  "confidence": 0.7615,
  "model_score": 0.8051,
  "style_score": 0.4038,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### FP04 — `false_positive`

*Targeting:* a student essay written to a rubric

```json
{
  "id": "FP04",
  "status": 200,
  "content_id": "b64dd67d-7ed5-438e-9052-0f3379139431",
  "creator_id": "attacker_FP04",
  "guess": "unsure",
  "confidence": 0.7579,
  "model_score": 0.8329,
  "style_score": 0.3796,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### FP05 — `false_positive`

*Targeting:* technical documentation written by a person

```json
{
  "id": "FP05",
  "status": 200,
  "content_id": "7a933a48-3189-4a94-bc6b-dea32520955b",
  "creator_id": "attacker_FP05",
  "guess": "unsure",
  "confidence": 0.6873,
  "model_score": 0.8005,
  "style_score": 0.4798,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### FP06 — `false_positive`

*Targeting:* a person imitating a formal template

```json
{
  "id": "FP06",
  "status": 200,
  "content_id": "12997357-0a53-4e3f-bdff-70645c0e3b6c",
  "creator_id": "attacker_FP06",
  "guess": "unsure",
  "confidence": 0.706,
  "model_score": 0.8814,
  "style_score": 0.3808,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### FP07 — `false_positive`

*Targeting:* human writing that repeats a phrase deliberately

```json
{
  "id": "FP07",
  "status": 200,
  "content_id": "7d42a06c-e2e8-4811-8a60-4380d454cd8e",
  "creator_id": "attacker_FP07",
  "guess": "unsure",
  "confidence": 0.6138,
  "model_score": 0.8816,
  "style_score": 0.4691,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### FP08 — `false_positive`

*Targeting:* very short genuine human submission

```json
{
  "id": "FP08",
  "status": 200,
  "content_id": "5c30935a-8532-4db3-9937-2c45833c93db",
  "creator_id": "attacker_FP08",
  "guess": "unsure",
  "confidence": 0.8608,
  "model_score": 0.3223,
  "style_score": 0.524,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### PI01 — `prompt_injection`

*Targeting:* instruction to ignore the check

```json
{
  "id": "PI01",
  "status": 200,
  "content_id": "3143c09e-3157-4d43-8883-2530d867956c",
  "creator_id": "attacker_PI01",
  "guess": "unsure",
  "confidence": 0.7546,
  "model_score": 0.4625,
  "style_score": 0.282,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### PI02 — `prompt_injection`

*Targeting:* instruction disguised as a system message

```json
{
  "id": "PI02",
  "status": 200,
  "content_id": "3ba38da5-2f0c-41cf-92cf-c0db24ec226e",
  "creator_id": "attacker_PI02",
  "guess": "unsure",
  "confidence": 0.5115,
  "model_score": 0.2044,
  "style_score": 0.3066,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### PI03 — `prompt_injection`

*Targeting:* instruction wrapped in the writer's voice

```json
{
  "id": "PI03",
  "status": 200,
  "content_id": "0c9acbab-e5d9-4222-98b6-97b13429fa68",
  "creator_id": "attacker_PI03",
  "guess": "unsure",
  "confidence": 0.9621,
  "model_score": 0.5943,
  "style_score": 0.3492,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### PI04 — `prompt_injection`

*Targeting:* attempt to make the label text hostile

```json
{
  "id": "PI04",
  "status": 200,
  "content_id": "0f3a5309-9c62-4884-b5b1-70f9b9d41605",
  "creator_id": "attacker_PI04",
  "guess": "unsure",
  "confidence": 0.9448,
  "model_score": 0.4998,
  "style_score": 0.4272,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### PI05 — `prompt_injection`

*Targeting:* attempt to inject into the audit log

```json
{
  "id": "PI05",
  "status": 200,
  "content_id": "e8367556-8dc5-4fb1-b975-f20f7e178117",
  "creator_id": "attacker_PI05",
  "guess": "unsure",
  "confidence": 0.756,
  "model_score": 0.6401,
  "style_score": 0.5741,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### PI06 — `prompt_injection`

*Targeting:* instruction plus real human text

```json
{
  "id": "PI06",
  "status": 200,
  "content_id": "51a63a51-d15d-4c95-8eef-dd650992713b",
  "creator_id": "attacker_PI06",
  "guess": "unsure",
  "confidence": 0.971,
  "model_score": 0.5583,
  "style_score": 0.3939,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### MF01 — `malformed`

*Targeting:* text is only whitespace

```json
{
  "id": "MF01",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF01",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF02 — `malformed`

*Targeting:* text is a single character

```json
{
  "id": "MF02",
  "status": 422,
  "content_id": "ec7602af-464f-4728-9490-2bb757e678d9",
  "creator_id": "attacker_MF02",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF03 — `malformed`

*Targeting:* text is control characters

```json
{
  "id": "MF03",
  "status": 200,
  "content_id": "9aa7edca-b855-4258-bf83-794473b666b8",
  "creator_id": "attacker_MF03",
  "guess": "human",
  "confidence": 0.516,
  "model_score": 0.0,
  "style_score": 0.4841,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### MF04 — `malformed`

*Targeting:* text is only punctuation

```json
{
  "id": "MF04",
  "status": 200,
  "content_id": "231e5bcb-1af6-4c16-b134-29bfb0003dd8",
  "creator_id": "attacker_MF04",
  "guess": "unsure",
  "confidence": 0.6852,
  "model_score": 0.0112,
  "style_score": 0.6667,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### MF05 — `malformed`

*Targeting:* text is a very long single word

```json
{
  "id": "MF05",
  "status": 200,
  "content_id": "ee30ad1c-9056-4597-925d-8d4fc75b8f66",
  "creator_id": "attacker_MF05",
  "guess": "unsure",
  "confidence": 0.8079,
  "model_score": 0.9976,
  "style_score": 0.1667,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### MF06 — `malformed`

*Targeting:* text is emoji only

```json
{
  "id": "MF06",
  "status": 200,
  "content_id": "a9c6225f-9bc4-4346-b30f-853e36551843",
  "creator_id": "attacker_MF06",
  "guess": "unsure",
  "confidence": 0.6352,
  "model_score": 0.9969,
  "style_score": 0.3333,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### MF07 — `malformed`

*Targeting:* text is right-to-left script

```json
{
  "id": "MF07",
  "status": 200,
  "content_id": "5c0accca-6b33-4652-b894-0aba210f37ab",
  "creator_id": "attacker_MF07",
  "guess": "unsure",
  "confidence": 0.87,
  "model_score": 0.9064,
  "style_score": 0.1984,
  "label": "The signals are inconclusive. This system cannot determine who wrote the text.",
  "error": null,
  "verdict": ""
}
```

### MF08 — `malformed`

*Targeting:* text is 60,000 characters

```json
{
  "id": "MF08",
  "status": 413,
  "content_id": null,
  "creator_id": "attacker_MF08",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ01 — `malformed`

*Targeting:* no text field at all

```json
{
  "id": "RQ01",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ01",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ02 — `malformed`

*Targeting:* no creator_id

```json
{
  "id": "RQ02",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ03 — `malformed`

*Targeting:* text is a number

```json
{
  "id": "RQ03",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ03",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ04 — `malformed`

*Targeting:* text is a list

```json
{
  "id": "RQ04",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ04",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ05 — `malformed`

*Targeting:* text is null

```json
{
  "id": "RQ05",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ05",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ06 — `malformed`

*Targeting:* creator_id is an object

```json
{
  "id": "RQ06",
  "status": 400,
  "content_id": null,
  "creator_id": {
    "id": "x"
  },
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ07 — `malformed`

*Targeting:* body is a JSON array, not an object

```json
{
  "id": "RQ07",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ08 — `malformed`

*Targeting:* body is unparseable JSON

```json
{
  "id": "RQ08",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ09 — `malformed`

*Targeting:* body is empty

```json
{
  "id": "RQ09",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ10 — `malformed`

*Targeting:* body is form-encoded, not JSON

```json
{
  "id": "RQ10",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ11 — `malformed`

*Targeting:* body is JSON claiming to be plain text

```json
{
  "id": "RQ11",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ12 — `malformed`

*Targeting:* deeply nested JSON

```json
{
  "id": "RQ12",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ12",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_01 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_01",
  "status": 200,
  "content_id": "ef38fe85-1b83-4824-96fa-f5e3d35cd3d1",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_02 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_02",
  "status": 200,
  "content_id": "71d9bd58-9995-478e-a90c-e45ff4df2b4a",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_03 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_03",
  "status": 200,
  "content_id": "3c7aab9a-5929-49a7-b4a4-92f6f2715578",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_04 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_04",
  "status": 200,
  "content_id": "65be1052-8476-4c0a-b201-53db70138746",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_05 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_05",
  "status": 200,
  "content_id": "26b7289a-3d4e-4bd6-a41c-e84dc282e166",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_06 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_06",
  "status": 200,
  "content_id": "7a7f6749-6764-44f2-985e-b8f2c0e9b98c",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_07 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_07",
  "status": 200,
  "content_id": "ef7e19b9-56c0-4676-84b7-ef4e8d1a1234",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_08 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_08",
  "status": 200,
  "content_id": "141ffd05-effb-4a6b-825c-6f37c3a64e1b",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_09 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_09",
  "status": 200,
  "content_id": "612402fb-840c-4e09-a4a1-ef9f6e35dd12",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_10 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_10",
  "status": 200,
  "content_id": "cd60bf9f-105b-4791-a5ac-adbdef429b50",
  "creator_id": "attacker_flood",
  "guess": "human",
  "confidence": 0.744,
  "model_score": 0.0287,
  "style_score": 0.2273,
  "label": "High-confidence human-like patterns: this system's signals are strongly associated with human writing. This is not proof of authorship.",
  "error": null,
  "verdict": ""
}
```

### FL01_11 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_11",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_12 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_12",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```
