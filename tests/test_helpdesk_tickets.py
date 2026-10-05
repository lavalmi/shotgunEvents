"""Offline checks for the daemon's helpdesk email summaries."""

import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import shotgunEventDaemon as daemon
from create_ticket import format_error_ticket


class HelpdeskTicketTests(unittest.TestCase):
    def test_critical_event_email(self):
        logger = logging.Logger("plugin.sgd_create_folders.daemon_callback")
        handler = daemon.HelpdeskTicketHandler(logging.CRITICAL)
        handler.setFormatter(logging.Formatter(daemon.EMAIL_FORMAT_STRING))
        logger.addHandler(handler)
        event = {
            'project': {'id': 4855, 'name': 'Publisher_Test', 'type': 'Project'},
            'entity': {'id': 105193, 'name': 'Light', 'type': 'Task'},
            'event_type': 'Shotgun_Task_Change',
            'attribute_name': 'task_assignees',
            'id': 21813506,
            'user': {'id': 3642, 'name': 'Oleg Bekker', 'type': 'HumanUser'},
        }
        with patch.object(daemon, "create_ticket") as send:
            logger.error("ordinary error")
            send.assert_not_called()
            logger.critical(
                "Original traceback and diagnostics",
                extra={"shotgrid_event": event, "exception_type": "TankError"},
            )
            send.assert_called_once()
        subject, body = send.call_args[0]
        self.assertEqual(subject, "[SGD] CRITICAL - SG event daemon.")
        self.assertEqual(body.split("\n\n")[0], "\n".join([
            "Project: Publisher_Test (4855)",
            "Plugin/logger: plugin.sgd_create_folders.daemon_callback",
            "Event: Shotgun_Task_Change",
            "Changed field: task_assignees",
            "Entity: Task \u201cLight\u201d (105193)",
            "Event ID: 21813506",
            "Triggered by: Oleg Bekker",
        ]))
        self.assertIn("Original traceback and diagnostics", body)

    def test_missing_context_and_exception_info(self):
        try:
            raise ValueError("test failure")
        except ValueError:
            record = logging.LogRecord("engine", logging.CRITICAL, __file__, 1,
                                       "failure", (), sys.exc_info())
        subject, body = format_error_ticket(record, "details")
        self.assertEqual(subject, "[SGD] CRITICAL - SG event daemon.")
        self.assertNotIn("Project:", body)
        self.assertNotIn("Triggered by:", body)
        self.assertTrue(body.endswith("details"))

    def test_summary_failure_still_sends_original_log(self):
        handler = daemon.HelpdeskTicketHandler(logging.CRITICAL)
        handler.setFormatter(logging.Formatter(daemon.EMAIL_FORMAT_STRING))
        record = logging.LogRecord("engine", logging.CRITICAL, __file__, 1,
                                   "Original error", (), None)
        original = handler.format(record)
        with patch.object(daemon, "format_error_ticket", side_effect=ValueError("bad data")), \
                patch.object(daemon, "create_ticket") as send:
            handler.emit(record)
        send.assert_called_once_with("[SGD] CRITICAL - SG event daemon.", original)

    def test_malformed_context_is_skipped(self):
        record = logging.LogRecord("engine", logging.CRITICAL, __file__, 1,
                                   "failure", (), None)
        record.shotgrid_event = {"project": [], "entity": "bad", "user": 3, "meta": []}
        subject, body = format_error_ticket(record, "original log")
        self.assertNotIn("Project:", body)
        self.assertNotIn("Entity:", body)
        self.assertTrue(body.endswith("original log"))

    def test_nullable_event_links_and_multiline_names(self):
        record = logging.LogRecord("engine", logging.CRITICAL, __file__, 1,
                                   "failure", (), None)
        record.shotgrid_event = {
            "project": {"name": "Project\r\nName"},
            "entity": None, "user": None,
            "meta": {"attribute_name": "sg_status_list"},
        }
        subject, body = format_error_ticket(record, "details")
        self.assertNotIn("\n", subject)
        self.assertNotIn("\r", subject)
        self.assertIn("Changed field: sg_status_list", body)

    def test_reconfiguration_removes_both_email_handlers(self):
        logger = logging.Logger("test")
        logger.addHandler(logging.handlers.SMTPHandler("unused", "unused", ["unused"], "unused"))
        logger.addHandler(daemon.HelpdeskTicketHandler(logging.CRITICAL))
        daemon._removeHandlersFromLogger(
            logger, (logging.handlers.SMTPHandler, daemon.HelpdeskTicketHandler)
        )
        self.assertEqual(logger.handlers, [])


if __name__ == "__main__":
    unittest.main()
