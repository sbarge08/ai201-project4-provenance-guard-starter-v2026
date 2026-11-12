"""AI-assisted Unit 9 evaluator: real HTTP, real GPT-2, immutable source per phase.

Run with the existing Python environment against a clean local clone. Outputs
are synthetic fixtures, real responses, log excerpts and timings, not authorship
accuracy measurements. The caller must commit criteria before invoking this.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE = "http://127.0.0.1:5000"
MAX_WARM_MS = 500.0
LOG_FIELDS = {
    "timestamp", "request_started_at", "request_completed_at", "duration_ms",
    "method", "endpoint", "status_code", "outcome", "content_id", "error_code",
    "request_id",  # Optional correlation metadata; no raw request header accepted.
}


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(root):
    return {p.name: sha(p) for p in sorted(root.glob("*.py"))}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def events(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def http(path, payload=None, timeout=180):
    request = Request(BASE + path,
                      data=None if payload is None else json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"},
                      method="GET" if payload is None else "POST")
    started = time.perf_counter()
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response:
        body_text = response.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError:
            body = {"non_json_response": body_text}
        return {
            "status": response.status,
            "body": body,
            "duration_header_ms": response.headers.get("X-Request-Duration-Ms"),
            "request_id_header": response.headers.get("X-Request-Id"),
            "client_seconds": time.perf_counter() - started,
        }


def submit(log, name, payload):
    previous = len(events(log))
    result = {"case": name, "payload": payload, "sent_at": now(),
              "log_start_line": previous + 1}
    result["response"] = http("/submit", payload)
    new_events = events(log)[previous:]
    result["events"] = new_events
    result["one_submit_event"] = len(new_events) == 1 and new_events[0].get("endpoint") == "/submit"
    return result


def valid_fixtures():
    paragraphs = [
        "This is synthetic writing for a local service test. A small garden needs water, sunlight, and careful observation. The gardener records changes each week. ",
        "This fictional example describes a library visit. A reader compares two books, writes a short note, and returns them before closing. No real personal information is included. ",
        "This generated test passage discusses a classroom experiment. The group measures the same object twice and records each result instead of assuming they agree. ",
    ]
    sizes = [100, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 4500]
    return [(paragraphs[i % 3] * (size // len(paragraphs[i % 3]) + 1))[:size]
            for i, size in enumerate(sizes)]


def invalid_fixtures(prefix):
    base = {"creator_id": prefix, "text": "This synthetic request contains enough words for a valid classification."}
    cases = []
    for i, (name, value) in enumerate([
        ("missing_text", "MISSING"), ("empty_text", ""), ("whitespace_text", " \t\n"),
        ("numeric_text", 42), ("null_text", None), ("list_text", ["test"]),
        ("object_text", {"test": "value"}), ("boolean_text", True),
    ]):
        payload = {**base, "creator_id": f"{prefix}-{i}"}
        if name == "missing_text":
            payload.pop("text")
        else:
            payload["text"] = value
        cases.append((name, payload, 400))
    cases += [("missing_creator", {"text": base["text"]}, 400),
              ("overlong_text", {**base, "text": "x" * 5001}, 413)]
    return cases


def privacy_fixtures(prefix):
    cases = []
    for i in range(10):
        marker = f"PRIVATE_SYNTHETIC_MARKER_{i:02d}_CAPSTONE"
        text = marker + ". This invented passage checks whether private writing is copied into operational monitoring. " * (i + 2)
        payload = {"text": text, "creator_id": f"{prefix}-{i}"}
        expected = 200
        if 5 <= i < 8:
            payload.pop("creator_id")
            expected = 400
        elif i >= 8:
            payload["text"] = (marker + ". " + "Synthetic long privacy example. " * 200)[:5001]
            expected = 413
        cases.append((f"privacy-{i}", marker, payload, expected))
    return cases


def matched(record, expected_success):
    if not record["one_submit_event"]:
        return False
    response, event = record["response"], record["events"][0]
    if event.get("status_code") != response["status"]:
        return False
    if expected_success:
        return (response["status"] == 200 and event.get("outcome") == "success"
                and bool(response["body"].get("content_id"))
                and event.get("content_id") == response["body"].get("content_id"))
    return 400 <= response["status"] < 500 and event.get("outcome") == "rejected"


def strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return list(value.keys()) + [s for v in value.values() for s in strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings(v)]
    return []


def privacy_leaks(records):
    found = []
    for record in records:
        text = record["payload"]["text"]
        probes = {record["marker"], text, text[:24], text[-24:], text[len(text)//2:len(text)//2+24]}
        for event in record["events"]:
            unexpected = sorted(set(event) - LOG_FIELDS)
            if unexpected:
                found.append({"case": record["case"], "unexpected_fields": unexpected})
            for value in strings(event):
                for probe in probes:
                    if len(probe.strip()) >= 16 and probe in value:
                        found.append({"case": record["case"], "leaked_probe": probe})
    return found


def correlation(records):
    rejected = [r for r in records if 400 <= r["response"]["status"] < 500]
    paired = [r for r in rejected if r["one_submit_event"]
              and r["response"].get("request_id_header")
              and r["response"]["request_id_header"] == r["events"][0].get("request_id")]
    return {"rejected_requests": len(rejected), "matching_request_ids": len(paired)}


def run_trial(root, output, phase, trial, expected_hashes):
    if source_hashes(root) != expected_hashes:
        raise RuntimeError("Source changed between trials")
    with socket.socket() as port_check:
        if port_check.connect_ex(("127.0.0.1", 5000)) == 0:
            raise RuntimeError("Port 5000 is already occupied; no existing process was stopped")
    log = root / "logs" / "operations.jsonl"
    offset = len(events(log))
    env = os.environ.copy()
    env.update(HOST="127.0.0.1", PORT="5000", AI201_DEBUG="0", AI201_DETECTOR_MODEL="gpt2",
               AI201_RATE_LIMITS="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               PYTHONIOENCODING="utf-8")
    data = {"trial": trial, "started_at": now(), "source_hashes": expected_hashes,
            "startup": {"command": [sys.executable, "-u", "app.py"], "cwd": str(root),
                        "reused_environment_and_cached_model": True,
                        "environment": {k: env[k] for k in ("HOST", "PORT", "AI201_DEBUG", "AI201_DETECTOR_MODEL", "AI201_RATE_LIMITS", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}}}
    process_log = output / f"{phase}-trial-{trial}-server.txt"
    with process_log.open("w", encoding="utf-8") as stream:
        proc = subprocess.Popen([sys.executable, "-u", "app.py"], cwd=root, env=env,
                                stdout=stream, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        data["startup"]["pid"] = proc.pid
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(f"Server exited with {proc.returncode}; inspect {process_log}")
                try:
                    health = http("/health", timeout=5)
                    if health["status"] == 200:
                        data["startup"]["health"] = health
                        data["startup"]["success"] = True
                        break
                except (URLError, OSError):
                    time.sleep(0.25)
            else:
                raise RuntimeError("Startup did not return HTTP 200 within 60 seconds")
            data["ping"] = http("/ping", {"message": "capstone-control"})
            prefix = f"capstone-{phase}-{trial}"
            data["warmup"] = submit(log, "warmup", {"text": valid_fixtures()[2], "creator_id": prefix+"-warmup"})
            if data["warmup"]["response"]["status"] != 200:
                raise RuntimeError("Warmup failed; real model classification is required")
            data["classifications"] = [submit(log, f"warm-{i+1}", {"text": text, "creator_id": f"{prefix}-warm-{i}"})
                                       for i, text in enumerate(valid_fixtures())]
            data["privacy"] = []
            for name, marker, payload, expected in privacy_fixtures(prefix+"-privacy"):
                record = submit(log, name, payload)
                record.update(marker=marker, expected_status=expected)
                data["privacy"].append(record)
            data["invalid"] = []
            for name, payload, expected in invalid_fixtures(prefix+"-invalid"):
                record = submit(log, name, payload)
                record["expected_status"] = expected
                data["invalid"].append(record)
            successes = sum(matched(r, True) for r in data["classifications"])
            durations = [r["events"][0]["duration_ms"] for r in data["classifications"] if matched(r, True)]
            leaks = privacy_leaks(data["privacy"])
            privacy_observed = all(r["response"]["status"] == r["expected_status"]
                                   and matched(r, r["expected_status"] == 200) for r in data["privacy"])
            rejected = sum(r["response"]["status"] == r["expected_status"] and matched(r, False) for r in data["invalid"])
            data["summary"] = {
                "logging": {"matched": successes, "total": 10, "met": successes == 10},
                "timing": {"durations_ms": durations, "max_ms": max(durations) if durations else None,
                           "mean_ms": statistics.mean(durations) if durations else None,
                           "within_limit": sum(d <= MAX_WARM_MS for d in durations), "total": 10,
                           "met": len(durations) == 10 and all(d <= MAX_WARM_MS for d in durations)},
                "privacy": {"leaks": leaks, "observed_all_10": privacy_observed,
                            "met": privacy_observed and not leaks},
                "invalid": {"matched": rejected, "total": 10, "met": rejected == 10},
                "startup": {"met": data["startup"]["success"]},
                "rejection_correlation_diagnostic": correlation(data["privacy"] + data["invalid"]),
            }
        finally:
            if proc.poll() is None:
                proc.terminate()  # Only the process this runner created.
            proc.wait(timeout=20)
            data["startup"]["stop_method"] = "terminate owned server process; manual Ctrl+C not tested"
            data["startup"]["stopped"] = proc.poll() is not None
            data["completed_at"] = now()
            data["operational_events"] = events(log)[offset:]
            (output / f"{phase}-trial-{trial}-operations.jsonl").write_text(
                "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in data["operational_events"]), encoding="utf-8")
            save_json(output / f"{phase}-trial-{trial}.json", data)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Clean committed clone; service writes logs here")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    root, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if list(output.glob(f"{args.phase}-trial-*.json")):
        raise RuntimeError("Refusing to overwrite preserved trials; use a new output directory")
    if git(root, "status", "--porcelain"):
        raise RuntimeError("Source clone must be clean before the phase starts")
    criteria_commit = git(root, "log", "-1", "--format=%H", "--", "criteria.md")
    committed = git(root, "show", f"{criteria_commit}:criteria.md")
    if "## Unit 9 Capstone" not in committed:
        raise RuntimeError("No committed capstone criteria found")
    manifest = {"phase": args.phase, "started_at": now(), "source_commit": git(root, "rev-parse", "HEAD"),
                "criteria_commit": criteria_commit, "criteria_sha256": sha(root / "criteria.md"),
                "python": sys.version, "platform": platform.platform(),
                "fixture_origin": "AI-generated synthetic operational test text; no human-authorship claims",
                "runner_sha256": sha(Path(__file__)), "trials": []}
    hashes = source_hashes(root)
    for trial in range(1, 4):
        result = run_trial(root, output, args.phase, trial, hashes)
        manifest["trials"].append(result["summary"])
        save_json(output / f"{args.phase}-summary.json", manifest)
        print(json.dumps({"phase": args.phase, "trial": trial, "summary": result["summary"]}), flush=True)
    if source_hashes(root) != hashes:
        raise RuntimeError("Source changed during evaluation")
    manifest["completed_at"] = now()
    manifest["verdicts"] = {name: "MET" if all(t[name]["met"] for t in manifest["trials"]) else "MISSED"
                            for name in ("logging", "timing", "privacy", "invalid", "startup")}
    save_json(output / f"{args.phase}-summary.json", manifest)
    print(json.dumps({"verdicts": manifest["verdicts"]}), flush=True)


if __name__ == "__main__":
    main()
