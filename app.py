#!/usr/bin/env python3
"""
Provenance Guard — the web service.

    python app.py

Then, in another terminal:

    curl -X POST http://127.0.0.1:5000/ping \
      -H "Content-Type: application/json" \
      -d '{"message": "hello"}'

That's the example route. It works right now, before you've written anything.
**Leave it alone** — it's your control. When something breaks later, check that
`/ping` still answers: if it does, the problem is in your handler; if it
doesn't, it's the service itself.

Routes:

    POST /ping        the worked example. Already works. Don't edit it
    POST /submit      ← YOU BUILD THIS (Milestone 3, 4, 5)
    POST /appeal      ← YOU BUILD THIS (Milestone 5)
    GET  /log         the audit log. Already works
    GET  /health      is the service up, and is the model loaded
"""

import uuid

from flask import Flask, jsonify, request

import audit
import config
import detector

app = Flask(__name__)


# ── Rate limiting — UNIT 8 ────────────────────────────────────────────────────
# Off until you turn it on. In unit 8, Milestone 1:
#
#   1. Set RATE_LIMITING_ENABLED = True in config.py (or AI201_RATE_LIMITS=1)
#   2. Choose your numbers there
#   3. Uncomment the @limiter.limit(...) line on /submit below
#
# The order doesn't matter. While limiting is off, that decorator is a no-op
# that quietly does nothing, so uncommenting it early costs you nothing — but
# it also means no 429 until you've done step 1.
#
# The storage backend is preconfigured, which stops Flask-Limiter printing a
# warning on every start. In-memory is right for one laptop and wrong for
# anything real — a restart forgets every count.

class _LimiterOff:
    """
    Stands in for the real limiter while rate limiting is off.

    It makes @limiter.limit(...) a decorator that returns the route
    untouched, so uncommenting the line before you flip the setting is
    harmless instead of a crash on startup.
    """

    def limit(self, *args, **kwargs):
        return lambda view: view


limiter = _LimiterOff()
if config.RATE_LIMITING_ENABLED:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    def rate_limit_key():
        """
        Who a request counts against.

        Falling back to the caller's address is the easy version. Unit 8's
        stretch asks about per-creator limits instead — and the difference
        matters: one script can look like a thousand callers, and one household
        can look like one.
        """
        payload = request.get_json(silent=True)
        # A body that parses as JSON but isn't an object — a bare list or
        # string — has no .get. Without this guard the key function raises
        # BEFORE the route runs, and a malformed request becomes a 500 that
        # looks like your handler crashed when your handler never ran.
        if not isinstance(payload, dict):
            return get_remote_address()
        creator = payload.get("creator_id")
        return creator if isinstance(creator, str) and creator.strip() else get_remote_address()

    limiter = Limiter(
        key_func=rate_limit_key,
        app=app,
        storage_uri=config.RATE_LIMIT_STORAGE,
        default_limits=[],
    )

    @app.errorhandler(429)
    def rate_limited(exc):
        """
        A rejected request still leaves a trace.

        ⚠️ An attack that shows up only as an absence is one you'll never find.
        """
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}
        audit.log_rejection(
            creator_id=payload.get("creator_id", "unknown"),
            reason="rate_limited",
            limit=str(exc.description),
        )
        return jsonify({
            "error": "rate_limited",
            "message": "Too many submissions. Try again shortly.",
            "limit": str(exc.description),
        }), 429


# ── The worked example. Already works. Don't edit. ────────────────────────────

@app.post("/ping")
def ping():
    """
    Everything a route needs, in six lines.

    JSON arrives as a dict. You pull things out of it. You return a dict and
    the framework turns it into a response. That's the whole idea.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "ok": True,
        "you_sent": payload.get("message"),
        "service": "provenance-guard",
    })


@app.get("/health")
def health():
    """Is the service up, and has the model been downloaded yet?"""
    import detector

    loaded = detector._model is not None
    return jsonify({
        "ok": True,
        "detector_model": config.DETECTOR_MODEL,
        "detector_loaded": loaded,
        "rate_limiting": config.RATE_LIMITING_ENABLED,
        "log_entries": len(audit.read_entries()),
    })


def _log_submission_rejection(creator_id: str, content_id: str, reason: str) -> None:
    try:
        audit.log_rejection(
            creator_id=creator_id,
            reason=reason,
            content_id=content_id,
        )
    except OSError:
        app.logger.exception("Could not log rejected content_id=%s", content_id)


# ── YOU BUILD THIS ────────────────────────────────────────────────────────────

@app.post("/submit")
# @limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute;{config.RATE_LIMIT_PER_DAY}/day")
def submit():
    """
    Validate a submission, calculate the model signal, and record its status.

    Expects JSON:
        {"text": "...", "creator_id": "..."}

    Stylometry and final scoring are not connected yet, so the response does
    not make an authorship classification.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({
            "error": "invalid_request",
            "message": "Request body must be a JSON object.",
        }), 400

    text = payload.get("text")
    creator_id = payload.get("creator_id")
    if not isinstance(text, str) or not text.strip():
        return jsonify({
            "error": "invalid_request",
            "message": "'text' must be a non-empty string.",
        }), 400
    if not isinstance(creator_id, str) or not creator_id.strip():
        return jsonify({
            "error": "invalid_request",
            "message": "'creator_id' must be a non-empty string.",
        }), 400
    if len(text) > 5000:
        return jsonify({
            "error": "text_too_long",
            "message": "'text' must not exceed 5000 characters.",
        }), 413

    content_id = str(uuid.uuid4())

    try:
        model_score = detector.model_signal(text)
    except ValueError as exc:
        _log_submission_rejection(creator_id, content_id, "unscorable_text")
        return jsonify({
            "error": "unscorable_text",
            "message": str(exc),
            "content_id": content_id,
        }), 422
    except detector.DetectorUnavailable:
        app.logger.exception("Detector unavailable for content_id=%s", content_id)
        _log_submission_rejection(creator_id, content_id, "detector_unavailable")
        return jsonify({
            "error": "detector_unavailable",
            "message": "The text could not be scored because the detector is unavailable.",
            "content_id": content_id,
        }), 503
    except Exception:
        app.logger.exception("Detector failed for content_id=%s", content_id)
        _log_submission_rejection(creator_id, content_id, "detector_error")
        return jsonify({
            "error": "detector_error",
            "message": "The detector could not score this submission.",
            "content_id": content_id,
        }), 503

    guess = "not_scored"
    label = "NOT FINAL / NOT SCORED - model signal only; this is not an authorship decision."
    try:
        audit.log_decision(
            content_id=content_id,
            creator_id=creator_id,
            guess=guess,
            model_score=model_score,
            style_score=None,
            combined_score=None,
            label=label,
            status="awaiting_stylometry",
        )
    except OSError:
        app.logger.exception("Could not write audit entry for content_id=%s", content_id)
        return jsonify({
            "error": "audit_unavailable",
            "message": "The score was calculated but could not be recorded.",
            "content_id": content_id,
        }), 503

    return jsonify({
        "content_id": content_id,
        "guess": guess,
        "confidence": None,
        "label": label,
        "model_score": model_score,
        "style_score": None,
        "stage": "model_signal_only",
    })


@app.post("/appeal")
def appeal():
    """
    A writer says you got it wrong. ← TODO — Milestone 5

    Expects JSON:
        {"content_id": "...", "reasoning": "..."}

    Should:
      1. Check the content_id actually exists — `audit.entries_for(id)` tells
         you. A typo here fails silently and looks like a broken endpoint,
         which is the single most common way this milestone eats an hour.
      2. Record the appeal with `audit.log_appeal(...)`, which moves the item
         to `under_review`.
      3. Confirm to the writer. No automatic re-checking needed.

    This is the smallest endpoint in the project and the one that matters most
    to the person on the other end. It's the only thing standing between a
    wrong accusation and nothing at all.
    """
    payload = request.get_json(silent=True) or {}

    # TODO: delete this and build the route.
    return jsonify({
        "error": "not_implemented",
        "message": "POST /appeal isn't built yet — see the TODO in app.py.",
        "you_sent": payload,
    }), 501


# ── Already works ─────────────────────────────────────────────────────────────

@app.get("/log")
def get_log():
    """
    The audit log, most recent last.

        curl "http://127.0.0.1:5000/log?limit=10"

    You need this in unit 8 to paste entries into your README, and you need it
    now to see whether your logging is actually working.
    """
    limit = request.args.get("limit", type=int)
    entries = audit.read_entries(limit=limit)
    return jsonify({"count": len(entries), "entries": entries})


def main():
    print(f"Provenance Guard on http://{config.HOST}:{config.PORT}")
    print(f"  detector model:  {config.DETECTOR_MODEL}")
    print(f"  rate limiting:   {'ON' if config.RATE_LIMITING_ENABLED else 'off (unit 8)'}")
    print(f"  audit log:       {config.AUDIT_LOG}")
    print()
    print("Check it's alive:")
    print(f'  curl -X POST http://{config.HOST}:{config.PORT}/ping \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"message\": \"hello\"}'")
    print()
    # debug=True hands out an interactive debugger, so it's local-only — see config.py
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
