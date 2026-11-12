import json
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import app as service
import config


class OperationalLoggingTests(unittest.TestCase):
    required_fields = {
        "timestamp",
        "request_started_at",
        "request_completed_at",
        "duration_ms",
        "method",
        "endpoint",
        "status_code",
        "outcome",
        "content_id",
        "error_code",
    }

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temporary_directory.name) / "logs"
        self._config_patches = [
            patch.object(config, "LOG_DIR", self.log_dir),
            patch.object(config, "AUDIT_LOG", self.log_dir / "audit.jsonl"),
            patch.object(config, "OPERATIONAL_LOG", self.log_dir / "operations.jsonl"),
        ]
        for config_patch in self._config_patches:
            config_patch.start()
        self._detector_patch = patch("app.detector.model_signal", return_value=0.2)
        self._style_patch = patch("app.stylometry.style_signal", return_value=0.4)
        self._detector_patch.start()
        self._style_patch.start()
        self.client = service.app.test_client()

    def tearDown(self):
        self._style_patch.stop()
        self._detector_patch.stop()
        for config_patch in reversed(self._config_patches):
            config_patch.stop()
        self.temporary_directory.cleanup()

    def read_events(self):
        if not config.OPERATIONAL_LOG.exists():
            return []
        return [
            json.loads(line)
            for line in config.OPERATIONAL_LOG.read_text(encoding="utf-8").splitlines()
        ]

    def assert_valid_event(self, event):
        self.assertTrue(self.required_fields <= event.keys())
        self.assertIsInstance(event["duration_ms"], (int, float))
        self.assertNotIsInstance(event["duration_ms"], bool)
        self.assertGreaterEqual(event["duration_ms"], 0)
        for field in ("timestamp", "request_started_at", "request_completed_at"):
            parsed = datetime.fromisoformat(event[field])
            self.assertIsNotNone(parsed.tzinfo)

    def test_successful_submission_has_complete_operational_record(self):
        response = self.client.post(
            "/submit",
            json={"text": "A test passage for the service.", "creator_id": "success-test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(float(response.headers["X-Request-Duration-Ms"]), 0)
        event = self.read_events()[-1]
        self.assert_valid_event(event)
        self.assertEqual(event["method"], "POST")
        self.assertEqual(event["endpoint"], "/submit")
        self.assertEqual(event["status_code"], 200)
        self.assertEqual(event["outcome"], "success")
        self.assertEqual(event["content_id"], response.get_json()["content_id"])
        self.assertIsNone(event["error_code"])

    def test_duration_includes_classification_execution(self):
        def delayed_model_signal(_text):
            time.sleep(0.05)
            return 0.2

        with patch("app.detector.model_signal", side_effect=delayed_model_signal):
            response = self.client.post(
                "/submit",
                json={"text": "timed classification", "creator_id": "timing-test"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(self.read_events()[-1]["duration_ms"], 40)

    def test_invalid_requests_are_logged_as_rejections(self):
        bad_request = self.client.post(
            "/submit",
            json={"text": " ", "creator_id": "invalid-400"},
        )
        too_long = self.client.post(
            "/submit",
            json={"text": "x" * 5001, "creator_id": "invalid-413"},
        )
        with patch("app.detector.model_signal", side_effect=ValueError("unscorable")):
            unscorable = self.client.post(
                "/submit",
                json={"text": "unscorable test", "creator_id": "invalid-422"},
            )

        self.assertEqual(
            [bad_request.status_code, too_long.status_code, unscorable.status_code],
            [400, 413, 422],
        )
        by_status = {event["status_code"]: event for event in self.read_events()}
        for status_code, error_code in (
            (400, "invalid_request"),
            (413, "text_too_long"),
            (422, "unscorable_text"),
        ):
            self.assert_valid_event(by_status[status_code])
            self.assertEqual(by_status[status_code]["outcome"], "rejected")
            self.assertEqual(by_status[status_code]["error_code"], error_code)

    def test_rate_limit_response_is_logged(self):
        responses = [
            self.client.post(
                "/submit",
                json={"text": "rate-limit test", "creator_id": "operational-429-test"},
            )
            for _ in range(11)
        ]

        self.assertEqual([response.status_code for response in responses][-1], 429)
        events = self.read_events()
        for event in events:
            self.assert_valid_event(event)
        event = next(event for event in events if event["status_code"] == 429)
        self.assert_valid_event(event)
        self.assertEqual(event["outcome"], "rejected")
        self.assertEqual(event["error_code"], "rate_limited")

    def test_server_error_is_logged_without_exception_detail(self):
        with patch("app.audit.read_entries", side_effect=RuntimeError("PRIVATE_EXCEPTION_DETAIL")):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 500)
        event = self.read_events()[-1]
        self.assert_valid_event(event)
        self.assertEqual(event["outcome"], "error")
        self.assertEqual(event["status_code"], 500)
        self.assertNotIn(
            "PRIVATE_EXCEPTION_DETAIL",
            config.OPERATIONAL_LOG.read_text(encoding="utf-8"),
        )

    def test_operational_log_does_not_contain_submitted_writing(self):
        private_writing = "PRIVATE_WRITING_SENTINEL_DO_NOT_LOG"
        response = self.client.post(
            "/submit",
            json={"text": private_writing, "creator_id": "privacy-test"},
        )

        self.assertEqual(response.status_code, 200)
        operational_log = config.OPERATIONAL_LOG.read_text(encoding="utf-8")
        self.assertNotIn(private_writing, operational_log)

    def test_existing_routes_and_classification_output_are_preserved(self):
        submission = self.client.post(
            "/submit",
            json={"text": "known test passage", "creator_id": "routes-test"},
        )
        self.assertEqual(submission.status_code, 200)
        result = submission.get_json()
        self.assertEqual(
            result,
            {
                "content_id": result["content_id"],
                "guess": "unsure",
                "confidence": 0.6042,
                "label": (
                    "The signals are inconclusive. This system cannot determine "
                    "who wrote the text."
                ),
                "model_score": 0.2,
                "style_score": 0.4,
                "combined_score": 0.3,
                "stage": "signals_combined_and_labeled",
            },
        )

        appeal = self.client.post(
            "/appeal",
            json={
                "content_id": result["content_id"],
                "reasoning": "This was written by me.",
            },
        )
        health = self.client.get("/health")
        audit_log = self.client.get("/log")
        ping = self.client.post("/ping", json={"message": "hello"})

        self.assertEqual(appeal.status_code, 200)
        self.assertEqual(appeal.get_json()["status"], "under_review")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(audit_log.status_code, 200)
        self.assertGreaterEqual(audit_log.get_json()["count"], 2)
        self.assertEqual(ping.status_code, 200)
        self.assertEqual(ping.get_json()["you_sent"], "hello")
        self.assertEqual(
            {event["endpoint"] for event in self.read_events()},
            {"/submit", "/appeal", "/health", "/log", "/ping"},
        )
        for event in self.read_events():
            self.assert_valid_event(event)


if __name__ == "__main__":
    unittest.main()
