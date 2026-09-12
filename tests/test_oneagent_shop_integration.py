from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from oneagent.app.core import OneAgentApplication
from oneagent.config import write_section_value
from oneagent.identity import load_identity
from oneagent.local_web import thumbs
from oneagent.local_web.server import LocalWebHost, start_local_web
from oneagent.local_web.settings import LocalWebSettings, local_web_page_url
from oneagent.local_web.shortlist import (
    backfill_shortlists_from_history, latest_shortlist, record_shortlist_from_task,
)
from oneagent.tasks.queue import TaskJob
from tests.test_oneagent_local_web import KETTLE_RESULT
from tests.test_oneagent_telegram import FakeTelegramClient


def shop_job() -> TaskJob:
    return TaskJob(
        id=6, chat_id=42, text="Find a travel kettle under $50",
        created_at="2026-09-12T00:00:00+00:00", status="completed", result=KETTLE_RESULT,
    )


class ShopIntegrationTests(unittest.TestCase):
    def test_identical_browser_messages_in_same_millisecond_are_distinct(self):
        with TemporaryDirectory() as directory:
            app = OneAgentApplication(load_identity(), Path(directory), FakeTelegramClient(allowed_chat_id=42))
            with patch("oneagent.app.core.time.time", return_value=123.0), patch.object(app, "_natural", side_effect=["first", "second"]):
                self.assertEqual(app.handle_local_web_message("same"), "first")
                self.assertEqual(app.handle_local_web_message("same"), "second")

    def test_browser_followup_includes_selected_product_and_replies_to_telegram(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            client = FakeTelegramClient(allowed_chat_id=42)
            app = OneAgentApplication(load_identity(), root, client)
            record_shortlist_from_task(shop_job(), KETTLE_RESULT, root=root)
            with patch.object(app, "_natural", return_value="Compare option two") as respond:
                reply = app.handle_local_web_message("compare this", "t6", 2)
            self.assertEqual(reply, "Compare option two")
            self.assertIn("Sakerplus", respond.call_args.args[1])
            self.assertIn("2. [currently viewing this tab]", respond.call_args.args[1])
            self.assertEqual(client.sent[-1], (42, reply))
            from oneagent.local_web.conversation import recent_conversation_turns
            turns = recent_conversation_turns(root=root, chat_id=42)
            self.assertEqual(turns[0]["message"], "compare this")
            self.assertEqual(turns[0]["reply"], reply)

    def test_task_result_and_status_link_use_bound_port(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            app = OneAgentApplication(load_identity(), root, FakeTelegramClient(allowed_chat_id=42))
            write_section_value("local_web", "port", "0", root)
            app._start_local_web()
            self.addCleanup(app._stop_local_web)
            self.assertIsNotNone(app._local_web)
            settings = app._local_web.settings
            self.assertGreater(settings.port, 0)
            record_shortlist_from_task(shop_job(), KETTLE_RESULT, root=root)
            url = local_web_page_url("t6", settings=settings)
            final = app._format_task_final(shop_job(), "completed", KETTLE_RESULT, page_url=url, shortlist_id="t6")
            self.assertIn(url, final)
            self.assertIn(url, app._local_web_status_line())
            from our_ark_telegram import telegram_message_chunks
            chunks = telegram_message_chunks(final, 4096)
            self.assertGreaterEqual(len(chunks), 4)
            self.assertIn("127.0.0.1", str(chunks[-1]))
            self.assertNotIn("merchant.example", str(chunks[-1]))

    def test_disabled_web_has_no_link_or_listener(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_section_value("local_web", "enabled", "false", root)
            app = OneAgentApplication(load_identity(), root, FakeTelegramClient(allowed_chat_id=42))
            app._start_local_web()
            self.assertIsNone(app._local_web)
            self.assertEqual(app._local_web_status_line(), "")
            self.assertEqual(local_web_page_url(root=root), "")

    def test_failed_history_is_never_promoted_and_old_failed_shortlist_is_removed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            record_shortlist_from_task(shop_job(), KETTLE_RESULT, root=root)
            for state in ("failed", "cancelled", "paused"):
                job = replace(shop_job(), status=state)
                self.assertIsNone(record_shortlist_from_task(job, KETTLE_RESULT, root=root))
                with patch("oneagent.local_web.shortlist.task_queue_status") as history:
                    history.return_value.history = [job]
                    self.assertEqual(backfill_shortlists_from_history(root), ())
                    self.assertIsNone(latest_shortlist(root=root))


class BrowserRequestTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.callback = Mock(return_value="answer")
        self.conversation_id = 42
        self.server = start_local_web(
            LocalWebHost(Path(self.directory.name), lambda: self.conversation_id, self.callback),
            settings=LocalWebSettings(enabled=True, host="127.0.0.1", port=0, token="test-token"),
        )
        self.addCleanup(self.server.stop)
        self.origin = f"http://127.0.0.1:{self.server.port}"

    def request(self, path, payload=None, *, authenticated=True):
        headers = {"Authorization": "Bearer test-token"} if authenticated else {}
        data = json.dumps(payload).encode() if payload is not None else None
        with urlopen(Request(self.origin + path, data=data, headers=headers), timeout=2) as response:
            return json.load(response)

    def result(self, request_id):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            result = self.request("/api/chat/" + request_id)
            if result["status"] != "pending":
                return result
            time.sleep(0.01)
        self.fail("Browser request did not complete")

    def test_repeated_messages_have_distinct_results(self):
        self.callback.side_effect = ["first answer", "second answer"]
        first = self.request("/api/chat", {"text": "same question"})
        self.assertEqual(self.result(first["request_id"])["reply"], "first answer")
        second = self.request("/api/chat", {"text": "same question"})
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertEqual(self.result(second["request_id"])["reply"], "second answer")
        with self.assertRaises(HTTPError) as denied:
            self.request("/api/chat/" + first["request_id"], authenticated=False)
        self.assertEqual(denied.exception.code, 401)

    def test_worker_exception_reaches_browser_without_exception_details(self):
        self.callback.side_effect = RuntimeError("private credential detail")
        accepted = self.request("/api/chat", {"text": "hello"})
        result = self.result(accepted["request_id"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("RuntimeError", result["reply"])
        self.assertNotIn("credential", result["reply"])

    def test_callback_error_message_is_available(self):
        self.callback.return_value = "OneAgent is stopping. Retry after restarting."
        accepted = self.request("/api/chat", {"text": "hello"})
        self.assertEqual(self.result(accepted["request_id"])["reply"], self.callback.return_value)

    def test_invalid_payload_and_unconfigured_chat_are_rejected(self):
        for payload in (["hello"], {"text": ["hello"]}, {"text": ""}):
            with self.assertRaises(HTTPError) as invalid:
                self.request("/api/chat", payload)
            self.assertEqual(invalid.exception.code, 400)
        self.conversation_id = None
        with self.assertRaises(HTTPError) as unconfigured:
            self.request("/api/chat", {"text": "hello"})
        self.assertEqual(unconfigured.exception.code, 409)
        self.callback.assert_not_called()


class ThumbnailDestinationTests(unittest.TestCase):
    def test_private_and_non_http_urls_never_open(self):
        for url in (
            "http://127.0.0.2/products/a", "http://10.0.0.5/a",
            "http://169.254.169.254/latest/meta-data/", "http://[::1]/a",
            "http://[::ffff:127.0.0.1]/a", "http://localhost./a", "file:///tmp/a",
        ):
            with self.subTest(url=url), patch.object(thumbs, "urlopen") as fetch:
                self.assertEqual(thumbs._download(url, accept="text/html"), b"")
                fetch.assert_not_called()

    def test_dns_private_or_mixed_answers_never_connect(self):
        for ips in (("10.0.0.5",), ("8.8.8.8", "127.0.0.1")):
            addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ips]
            with patch.object(thumbs.socket, "getaddrinfo", return_value=addresses), patch.object(thumbs.socket, "create_connection") as connect:
                with self.assertRaises(OSError):
                    thumbs._connect_public(("merchant.example", 443), 2)
                connect.assert_not_called()

    def test_public_dns_result_is_pinned_for_connection(self):
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        with patch.object(thumbs.socket, "getaddrinfo", return_value=addresses), patch.object(thumbs.socket, "create_connection") as connect:
            thumbs._connect_public(("merchant.example", 443), 2)
            connect.assert_called_once_with(("8.8.8.8", 443), 2, None)

    def test_redirect_to_private_host_is_rejected_before_following(self):
        handler = thumbs._PublicRedirectHandler()
        with self.assertRaises(URLError):
            handler.redirect_request(Request("https://merchant.example/a"), None, 302, "Found", {}, "http://192.168.1.1/a")


if __name__ == "__main__":
    unittest.main()
