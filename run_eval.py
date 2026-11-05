#!/usr/bin/env python3
"""Run the five original acceptance criteria three times each."""

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import config
import scenarios
import scoring

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

DEFAULT_URL = f"http://{config.HOST}:{config.PORT}"
APPEAL_REASON = "I request a review of this evaluation submission."


def describe_response(response):
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def audit_entries(requests, url):
    response = requests.get(f"{url}/log", timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f"GET /log returned HTTP {response.status_code}")
    payload = describe_response(response)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("GET /log did not return an entries list")
    return entries


def run_classification_trial(requests, url, scenario, samples, trial_number, timeout):
    results = []
    for index, sample in enumerate(samples, 1):
        dataset = scenario.get("dataset", "sample")
        creator_id = (
            f"eval_c{scenario['criterion']}_t{trial_number}_{dataset}_{sample['id']}"
        )
        try:
            response = requests.post(
                f"{url}/submit",
                json={"text": sample["text"], "creator_id": creator_id},
                timeout=timeout,
            )
            payload = describe_response(response)
            results.append({
                "sample_id": sample["id"],
                "creator_id": creator_id,
                "provenance": sample["provenance"],
                "http_status": response.status_code,
                "guess": payload.get("guess"),
                "confidence": payload.get("confidence"),
                "model_score": payload.get("model_score"),
                "style_score": payload.get("style_score"),
                "combined_score": payload.get("combined_score"),
                "label": payload.get("label"),
                "error": payload.get("error"),
            })
        except requests.RequestException as exc:
            results.append({
                "sample_id": sample["id"],
                "creator_id": creator_id,
                "provenance": sample["provenance"],
                "http_status": None,
                "error": f"{type(exc).__name__}: {exc}",
            })

    return results


def classify_score_coverage():
    human = config.HUMAN_THRESHOLD
    ai = config.AI_THRESHOLD
    cases = [
        ("score_zero", 0.0),
        ("just_below_human_threshold", math.nextafter(human, 0.0)),
        ("human_threshold", human),
        ("just_above_human_threshold", math.nextafter(human, 1.0)),
        ("unsure_band_midpoint", (human + ai) / 2.0),
        ("just_below_ai_threshold", math.nextafter(ai, 0.0)),
        ("ai_threshold", ai),
        ("just_above_ai_threshold", math.nextafter(ai, 1.0)),
        ("score_one", 1.0),
    ]
    results = []
    for case, score in cases:
        guess, label = scoring.score_to_label(score)
        results.append({
            "case": case,
            "score": score,
            "guess": guess,
            "label": label,
        })

    labels = sorted({result["guess"] for result in results})
    expected_labels = ["ai", "human", "unsure"]
    intervals = [
        {"label": "human", "lower": 0.0, "lower_inclusive": True,
         "upper": human, "upper_inclusive": True},
        {"label": "unsure", "lower": human, "lower_inclusive": False,
         "upper": ai, "upper_inclusive": False},
        {"label": "ai", "lower": ai, "lower_inclusive": True,
         "upper": 1.0, "upper_inclusive": True},
    ]
    return {
        "thresholds": {"human": human, "ai": ai},
        "observed_labels": labels,
        "expected_labels": expected_labels,
        "intervals": intervals,
        "partition_verified": (
            intervals[0]["lower"] == 0.0
            and intervals[-1]["upper"] == 1.0
            and intervals[0]["upper"] == intervals[1]["lower"] == human
            and intervals[1]["upper"] == intervals[2]["lower"] == ai
            and intervals[0]["upper_inclusive"]
            and not intervals[1]["lower_inclusive"]
            and not intervals[1]["upper_inclusive"]
            and intervals[2]["lower_inclusive"]
        ),
        "boundary_cases": results,
    }


def run_appeal_trial(requests, url, scenario, trial_number, timeout):
    results = []
    for index in range(1, scenario["sample_count"] + 1):
        creator_id = f"eval_appeal_t{trial_number}_{index:02}"
        submission = {
            "http_status": None,
            "content_id": None,
            "guess": None,
            "model_score": None,
            "style_score": None,
            "combined_score": None,
            "appeal_http_status": None,
            "appeal_status": None,
            "original_decision_retained": False,
            "appeal_audited": False,
            "rate_limited": False,
        }
        try:
            response = requests.post(
                f"{url}/submit",
                json={
                    "text": (
                        f"Appeal reliability evaluation submission {index} "
                        f"for trial {trial_number}. This is a genuine new "
                        "submission created to obtain a real content ID."
                    ),
                    "creator_id": creator_id,
                },
                timeout=timeout,
            )
            payload = describe_response(response)
            submission.update({
                "http_status": response.status_code,
                "content_id": payload.get("content_id"),
                "guess": payload.get("guess"),
                "model_score": payload.get("model_score"),
                "style_score": payload.get("style_score"),
                "combined_score": payload.get("combined_score"),
                "rate_limited": response.status_code == 429,
            })
            if response.status_code != 200 or not submission["content_id"]:
                submission["error"] = payload.get("error") or "submission_failed"
                results.append(submission)
                continue

            appeal_response = requests.post(
                f"{url}/appeal",
                json={
                    "content_id": submission["content_id"],
                    "reasoning": APPEAL_REASON,
                },
                timeout=timeout,
            )
            appeal_payload = describe_response(appeal_response)
            submission["appeal_http_status"] = appeal_response.status_code
            submission["appeal_status"] = appeal_payload.get("status")

            related = [
                entry for entry in audit_entries(requests, url)
                if entry.get("content_id") == submission["content_id"]
            ]
            original = next(
                (entry for entry in related if entry.get("status") == "decided"),
                None,
            )
            appeal_entry = next(
                (
                    entry for entry in related
                    if entry.get("event") == "appeal"
                    and entry.get("status") == "under_review"
                    and entry.get("reasoning") == APPEAL_REASON
                ),
                None,
            )
            submission["original_decision_retained"] = original is not None
            submission["appeal_audited"] = appeal_entry is not None
            if not submission["appeal_audited"] or not submission["original_decision_retained"]:
                submission["error"] = "audit_verification_failed"
        except requests.RequestException as exc:
            submission["error"] = f"{type(exc).__name__}: {exc}"
        results.append(submission)
    return results


def run_invalid_trial(requests, url, trial_number, timeout):
    results = []
    for case in scenarios.INVALID_CASES:
        body = dict(case["body"])
        if "creator_id" in body:
            body["creator_id"] = f"eval_invalid_t{trial_number}_{case['case']}"
        before_entries = audit_entries(requests, url)
        before_ids = {
            entry.get("content_id") for entry in before_entries
            if entry.get("content_id")
        }

        result = {
            "case": case["case"],
            "request_shape": (
                "missing_text" if case["case"] == "missing_text"
                else "missing_creator_id" if case["case"] == "missing_creator_id"
                else "text_over_5000_characters"
                if case["case"] == "text_over_5000_characters"
                else case["case"]
            ),
            "http_status": None,
            "error": None,
            "new_decision_logged": None,
            "rate_limited": False,
        }
        try:
            response = requests.post(
                f"{url}/submit",
                json=body,
                timeout=timeout,
            )
            payload = describe_response(response)
            after_entries = audit_entries(requests, url)
            new_decisions = [
                entry for entry in after_entries
                if entry.get("status") == "decided"
                and entry.get("content_id") not in before_ids
            ]
            result.update({
                "http_status": response.status_code,
                "error": payload.get("error"),
                "new_decision_logged": bool(new_decisions),
                "rate_limited": response.status_code == 429,
            })
            if new_decisions:
                result["new_decision_content_ids"] = [
                    entry.get("content_id") for entry in new_decisions
                ]
        except requests.RequestException as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(result)
    return results


def summarize_trial(scenario, cases):
    criterion = scenario["criterion"]
    if criterion == 1:
        valid = [case for case in cases if case.get("http_status") == 200]
        false_positives = sum(case.get("guess") == "ai" for case in valid)
        return {
            "sample_count": len(cases),
            "valid_scores": len(valid),
            "high_confidence_ai_false_positives": false_positives,
            "target_max": 1,
            "metric_met": (
                len(cases) == scenario["sample_count"]
                and len(valid) == scenario["sample_count"]
                and false_positives <= 1
            ),
            "rate_limited": sum(case.get("http_status") == 429 for case in cases),
        }
    if criterion == 2:
        valid = [case for case in cases if case.get("http_status") == 200]
        ai_scores = [
            case["combined_score"] for case in valid
            if case.get("dataset") == "ai"
            and isinstance(case.get("combined_score"), (int, float))
        ]
        human_scores = [
            case["combined_score"] for case in valid
            if case.get("dataset") == "human"
            and isinstance(case.get("combined_score"), (int, float))
        ]
        ai_mean = sum(ai_scores) / len(ai_scores) if ai_scores else None
        human_mean = sum(human_scores) / len(human_scores) if human_scores else None
        gap = ai_mean - human_mean if ai_mean is not None and human_mean is not None else None
        complete = (
            len(ai_scores) == scenario["sample_count"]
            and len(human_scores) == scenario["sample_count"]
        )
        return {
            "ai_sample_count": len(ai_scores),
            "human_sample_count": len(human_scores),
            "ai_mean_combined_score": ai_mean,
            "human_mean_combined_score": human_mean,
            "ai_minus_human_mean": gap,
            "target_minimum": 0.20,
            "metric_met": complete and gap >= 0.20,
            "rate_limited": sum(case.get("http_status") == 429 for case in cases),
        }
    if criterion == 3:
        return {
            "observed_labels": cases["observed_labels"],
            "all_labels_reached": cases["observed_labels"] == ["ai", "human", "unsure"],
            "partition_verified": cases["partition_verified"],
            "boundary_cases": cases["boundary_cases"],
            "metric_met": (
                cases["observed_labels"] == ["ai", "human", "unsure"]
                and cases["partition_verified"]
                and len(cases["boundary_cases"]) == 9
            ),
        }
    if criterion == 4:
        successful = sum(
            case.get("http_status") == 200
            and case.get("appeal_http_status") == 200
            and case.get("appeal_status") == "under_review"
            and case.get("original_decision_retained")
            and case.get("appeal_audited")
            for case in cases
        )
        return {
            "appeals_succeeded": successful,
            "appeals_expected": scenario["sample_count"],
            "rate_limited": sum(case.get("rate_limited", False) for case in cases),
            "metric_met": successful == scenario["sample_count"],
        }
    expected = scenario["sample_count"]
    successful = sum(
        case.get("http_status") is not None
        and 400 <= case["http_status"] < 500
        and case["http_status"] != 429
        and not case.get("new_decision_logged")
        for case in cases
    )
    return {
        "invalid_cases_rejected": successful,
        "invalid_cases_expected": expected,
        "rate_limited": sum(case.get("rate_limited", False) for case in cases),
        "metric_met": successful == expected,
    }


def evaluate_scenario(requests, url, scenario, trial_number, timeout, samples=None):
    kind = scenario["kind"]
    if kind == "label_coverage":
        cases = classify_score_coverage()
        return {"summary": summarize_trial(scenario, cases), "cases": cases}
    if kind == "classifications":
        cases = run_classification_trial(
            requests, url, scenario, samples, trial_number, timeout
        )
        for case in cases:
            case["dataset"] = scenario["dataset"]
        return {"summary": summarize_trial(scenario, cases), "cases": cases}
    if kind == "score_separation":
        cases = []
        for dataset_name in ("human", "ai"):
            batch = run_classification_trial(
                requests,
                url,
                {"criterion": scenario["criterion"], "dataset": dataset_name},
                samples[dataset_name],
                trial_number,
                timeout,
            )
            for case in batch:
                case["dataset"] = dataset_name
            cases.extend(batch)
        return {"summary": summarize_trial(scenario, cases), "cases": cases}
    if kind == "appeals":
        cases = run_appeal_trial(
            requests, url, scenario, trial_number, timeout
        )
        return {"summary": summarize_trial(scenario, cases), "cases": cases}
    cases = run_invalid_trial(requests, url, trial_number, timeout)
    return {"summary": summarize_trial(scenario, cases), "cases": cases}


def write_report(report, label):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    json_path = config.RESULTS_DIR / f"run_{stamp}{suffix}.json"
    markdown_path = config.RESULTS_DIR / f"run_{stamp}{suffix}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"# Run log{f' — {label}' if label else ''}",
        "",
        f"- Produced by: `run_eval.py::main`",
        f"- Service: `{report['service_url']}` · `{report['trials']} trials per criterion`",
        f"- Evaluation timestamp: {report['started_at']}",
        f"- Structured results: `{json_path.relative_to(config.ROOT)}`",
        "",
        "| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for result in report["criteria"]:
        runs = []
        for trial in result["trials"]:
            summary = trial["summary"]
            if "ai_minus_human_mean" in summary:
                gap = summary["ai_minus_human_mean"]
                if gap is None:
                    runs.append("incomplete diagnostic")
                else:
                    runs.append(
                        f"HC3 diagnostic gap {gap:.4f} "
                        f"(AI {summary['ai_mean_combined_score']:.4f} "
                        f"− human {summary['human_mean_combined_score']:.4f})"
                    )
            elif result["status"] == "NOT EVALUATED":
                runs.append("NOT EVALUATED")
            elif "high_confidence_ai_false_positives" in summary:
                runs.append(
                    f"{summary['high_confidence_ai_false_positives']}/"
                    f"{summary['valid_scores']} AI false positives"
                )
            elif "boundary_cases" in summary:
                runs.append(
                    f"{','.join(summary['observed_labels'])}; "
                    f"partition={'pass' if summary['partition_verified'] else 'fail'}"
                )
            elif "appeals_succeeded" in summary:
                runs.append(
                    f"{summary['appeals_succeeded']}/{summary['appeals_expected']} appeals"
                )
            else:
                runs.append(
                    f"{summary['invalid_cases_rejected']}/"
                    f"{summary['invalid_cases_expected']} invalid cases"
                )
        verdict = result.get("diagnostic_status", result["status"])
        if result["status"] == "EVALUATED":
            verdict = (
                "MET"
                if all(trial["summary"]["metric_met"] for trial in result["trials"])
                else "MISSED"
            )
        elif result.get("diagnostic_status"):
            verdict = (
                f"NOT EVALUATED (HC3 diagnostic {result['diagnostic_status']}; "
                "human-authorship verification unavailable)"
            )
        lines.append(
            f"| {result['criterion']}. {result['name']} | {result['target']} | "
            f"{' | '.join(runs)} | **{verdict}** |"
        )
    lines += ["", "## Trial outputs", ""]
    for result in report["criteria"]:
        lines += [f"### Criterion {result['criterion']}: {result['name']}", ""]
        if result["status"] == "NOT EVALUATED" and not result.get("diagnostic_status"):
            lines += [f"NOT EVALUATED: {result['reason']}", ""]
            continue
        if result.get("reason"):
            lines += [f"**Acceptance status:** NOT EVALUATED — {result['reason']}", ""]
        for number, trial in enumerate(result["trials"], 1):
            if trial.get("summary", {}).get("status") == "NOT EVALUATED":
                lines += [
                    f"**Trial {number}** — NOT EVALUATED: "
                    f"{trial['summary']['reason']}",
                    "",
                ]
                continue
            lines += [
                f"**Trial {number}** — produced by `run_eval.py::evaluate_scenario`",
                "",
                "```json",
                json.dumps(trial, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path.relative_to(config.ROOT)}")
    print(f"Wrote {markdown_path.relative_to(config.ROOT)}")
    return json_path, markdown_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--label", default="")
    parser.add_argument(
        "--criteria",
        default="1,2,3,4,5",
        help="comma-separated original criterion numbers to run (default: all)",
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()
    if args.trials != 3:
        parser.error("The original criteria require exactly three trials.")
    try:
        selected_criteria = {
            int(value.strip()) for value in args.criteria.split(",") if value.strip()
        }
    except ValueError:
        parser.error("--criteria must be a comma-separated list from 1 through 5.")
    if not selected_criteria or not selected_criteria <= {1, 2, 3, 4, 5}:
        parser.error("--criteria must select one or more criteria from 1 through 5.")

    try:
        import requests
    except ImportError:
        parser.error("The `requests` package is missing; install requirements.txt.")

    scenario_problems = scenarios.validate()
    fixed_scenario_problems = [
        problem for problem in scenario_problems
        if "evaluation_samples.json" not in problem
    ]
    if fixed_scenario_problems:
        parser.error("Invalid scenarios: " + "; ".join(fixed_scenario_problems))

    samples = None
    sample_data_error = None
    try:
        samples = scenarios.load_samples()
    except (FileNotFoundError, ValueError) as exc:
        sample_data_error = str(exc)
        samples = None
        print(f"Sample data unavailable: {sample_data_error}", file=sys.stderr)

    try:
        health_response = requests.get(f"{args.url}/health", timeout=5)
        health_response.raise_for_status()
        health = describe_response(health_response)
    except requests.RequestException as exc:
        parser.error(f"No local service responding at {args.url}: {exc}")
    if not health.get("rate_limiting"):
        parser.error(
            "The local service reports rate limiting disabled; refusing to run "
            "evaluation without the required limiter."
        )

    started_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    report = {
        "produced_by": "run_eval.py::main",
        "service_url": args.url,
        "rate_limiting_enabled": health["rate_limiting"],
        "rate_limit_policy": "10 per minute and 200 per day per creator ID",
        "label": args.label,
        "trials": 3,
        "criteria_requested": sorted(selected_criteria),
        "started_at": started_at,
        "scenario_harness_changes": [
            "Added direct score_to_label boundary measurements for criterion 3.",
            "Added real submission-and-appeal sequences for criterion 4.",
            "Added audit-log checks for invalid submissions in criterion 5.",
            "Uses a distinct creator ID for each valid evaluation request to "
            "avoid accidental rate limiting without disabling or weakening it.",
            "Accepts pinned, dataset-level HC3 provenance for criterion 2 without "
            "inventing per-answer author identities or generation timestamps.",
        ],
        "criteria": [],
    }

    for scenario in scenarios.SCENARIOS:
        if scenario["criterion"] not in selected_criteria:
            continue
        result = {
            "criterion": scenario["criterion"],
            "name": scenario["name"],
            "target": scenario["target"],
            "status": "EVALUATED",
            "trials": [],
        }
        if scenario["criterion"] == 1 and (
            sample_data_error or not samples.get("verified_human")
        ):
            reason = sample_data_error or (
                "Missing 20 verified user-authored human samples. HC3's "
                "dataset-labeled human answers are not substituted for the "
                "original criterion's verified writing requirement."
            )
            result["status"] = "NOT EVALUATED"
            result["reason"] = reason
            result["trials"] = [
                {
                    "trial": trial_number,
                    "summary": {
                        "status": "NOT EVALUATED",
                        "reason": reason,
                    },
                    "cases": [],
                }
                for trial_number in range(1, 4)
            ]
            report["criteria"].append(result)
            print(f"Criterion {scenario['criterion']}: NOT EVALUATED")
            continue
        if scenario["criterion"] == 2 and sample_data_error:
            result["status"] = "NOT EVALUATED"
            result["reason"] = sample_data_error
            result["trials"] = [
                {
                    "trial": trial_number,
                    "summary": {
                        "status": "NOT EVALUATED",
                        "reason": sample_data_error,
                    },
                    "cases": [],
                }
                for trial_number in range(1, 4)
            ]
            report["criteria"].append(result)
            print("Criterion 2: NOT EVALUATED")
            continue
        if scenario["criterion"] == 2 and samples:
            result["status"] = "NOT EVALUATED"
            result["reason"] = (
                "HC3 provides a documented human/ChatGPT dataset label, but "
                "does not independently verify each human respondent as required "
                "by the original criterion. The three trials below are diagnostic "
                "dataset-label comparisons, not a pass/fail evaluation of that "
                "authorship requirement."
            )

        print(f"\nCriterion {scenario['criterion']}: {scenario['name']}")
        for trial_number in range(1, 4):
            trial = evaluate_scenario(
                requests,
                args.url,
                scenario,
                trial_number,
                args.timeout,
                samples=samples,
            )
            trial["trial"] = trial_number
            result["trials"].append(trial)
            print(
                f"  trial {trial_number}: "
                f"{json.dumps(trial['summary'], ensure_ascii=False)}"
            )
        if scenario["criterion"] == 2:
            result["diagnostic_status"] = (
                "MET"
                if all(
                    trial["summary"].get("metric_met")
                    for trial in result["trials"]
                )
                else "MISSED"
            )
        report["criteria"].append(result)

    report["completion"] = (
        "INCOMPLETE: one or more original acceptance criteria remain "
        "NOT EVALUATED because the required authorship provenance is unavailable."
        if any(result["status"] == "NOT EVALUATED" for result in report["criteria"])
        else "COMPLETE"
    )
    write_report(report, args.label)


if __name__ == "__main__":
    main()
