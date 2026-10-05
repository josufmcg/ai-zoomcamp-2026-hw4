import json
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch

import server


class IncidentReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = server.IncidentStore(Path(self.temp_dir.name) / "incidents.db")
        self.store_patch = patch.object(server, "store", self.store)
        self.store_patch.start()
        self.executor = Mock()
        self.executor_patch = patch.object(server, "executor", self.executor)
        self.executor_patch.start()
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.IncidentHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.executor_patch.stop()
        self.store_patch.stop()
        self.temp_dir.cleanup()

    def post_alert(self, status="firing"):
        payload = {
            "receiver": "Incident Response",
            "status": status,
            "alerts": [
                {
                    "status": status,
                    "fingerprint": "test-fingerprint",
                    "startsAt": "2026-10-05T16:00:00Z",
                    "labels": {
                        "alertname": "Order Tracker 5xx responses",
                        "http_route": "/api/orders/{order_id}",
                    },
                    "annotations": {
                        "description": "5xx responses in the last 5 minutes",
                        "dashboard_url": "http://localhost:3000/d/order-tracker/order-tracker",
                    },
                }
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/alerts",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())

    def test_firing_alert_is_saved_and_queued_once(self):
        status, response = self.post_alert()
        self.assertEqual(status, 202)
        self.assertEqual(len(response["accepted"]), 1)
        incident_id = response["accepted"][0]["id"]
        record = self.store.get(incident_id)
        self.assertEqual(record["endpoint"], "/api/orders/{order_id}")
        self.assertEqual(record["assistant_status"], "queued")
        self.executor.submit.assert_called_once_with(server.run_assistant, incident_id)

        self.post_alert()
        self.executor.submit.assert_called_once()

    def test_resolved_alert_is_saved_without_starting_assistant(self):
        status, response = self.post_alert(status="resolved")
        self.assertEqual(status, 202)
        record = self.store.get(response["accepted"][0]["id"])
        self.assertEqual(record["status"], "resolved")
        self.assertEqual(record["assistant_status"], "not_started")
        self.executor.submit.assert_not_called()

    def test_headless_assistant_receives_incident_context_read_only(self):
        _, response = self.post_alert()
        incident_id = response["accepted"][0]["id"]
        with (
            patch.object(server, "collect_logs", return_value=[{"line": "HTTP 500"}]),
            patch.object(server, "collect_traces", return_value=[{"traceID": "abc123"}]),
            patch.object(server.shutil, "which", return_value="/usr/bin/claude"),
            patch.object(
                server.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, "Likely database error.", ""),
            ) as run,
        ):
            server.run_assistant(incident_id)

        record = self.store.get(incident_id)
        self.assertEqual(record["assistant_status"], "completed")
        self.assertEqual(json.loads(record["logs_json"]), [{"line": "HTTP 500"}])
        self.assertEqual(json.loads(record["traces_json"]), [{"traceID": "abc123"}])
        self.assertEqual(record["assistant_output"], "Likely database error.")
        command = run.call_args.args[0]
        self.assertIn("--permission-mode", command)
        self.assertIn("plan", command)
        self.assertEqual(command[command.index("--tools") + 1], "Read")
        self.assertIn("Do not edit files", command[-1])
        self.assertIn("/api/orders/{order_id}", command[-1])


if __name__ == "__main__":
    unittest.main()
