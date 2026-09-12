from http.cookiejar import CookieJar
import json
from pathlib import Path
import re
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit, parse_qs
from urllib.request import build_opener, HTTPCookieProcessor, Request

from oneagent.collaboration import HandoffStore
from oneagent.travel.demo import ControlServer
from oneagent.travel.server import Hub, SITES, WebServer
from oneagent.travel.telegram import TelegramDemo, existing_bot_reply


class HandoffTests(unittest.TestCase):
    def test_scope_expiry_replay_and_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HandoffStore(Path(directory) / "auth.sqlite")
            alice = store.account("alice", start=True)
            link = store.issue(alice, "flights")
            with self.assertRaises(PermissionError):
                store.redeem(link, "hotels")
            owner, csrf, cookie = store.redeem(link, "flights")
            self.assertEqual(owner, alice)
            self.assertEqual(store.browser(cookie, "flights"), (alice, csrf, None))
            with self.assertRaises(PermissionError):
                store.redeem(link, "flights")
            with self.assertRaises(PermissionError):
                store.redeem(store.issue(alice, "hotels", ttl=-1), "hotels")
            with self.assertRaises(PermissionError):
                store.browser(cookie, "hotels", allow_new=False)
            old = store.issue(alice, "hotels")
            self.assertNotEqual(store.account("alice", start=True, reset=True), alice)
            with self.assertRaises(PermissionError):
                store.redeem(old, "hotels")
            with self.assertRaises(PermissionError):
                store.browser(cookie, "flights", allow_new=False)


class TelegramTravelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seen = []
        def factory(owner):
            def respond(payload, key):
                self.seen.append((owner, key, payload))
                current = payload["current"]
                return {"text": f"[Fixture] {current['app_id']}; prior turns {len(payload['history'])}"}
            return respond
        self.factory = factory
        self.hub = Hub(self.root / "state", responder_factory=factory)
        self.addCleanup(lambda: self.hub.close())
        self.controller = TelegramDemo(self.hub)
        self.webs, self.browsers, self.boot = {}, {}, {}
        for site in SITES:
            (self.root / site).mkdir()
            (self.root / site / "index.html").write_text(f"<title>{site}</title>")
            server = WebServer(("127.0.0.1", 0), self.hub, self.root, app_id=site)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            self.webs[site] = server
            self.browsers[site] = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, site, route, body=None, browser=None, csrf=None):
        origin = self.webs[site].public_origin
        headers = {}
        if body is not None:
            headers = {"Content-Type": "application/json", "Origin": origin, "X-CSRF-Token": csrf or self.boot[site]["csrf"]}
        req = Request(origin + "/api/" + route, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with (browser or self.browsers[site]).open(req, timeout=5) as response:
            return json.load(response)

    def connect(self, text, sites=SITES):
        links = re.findall(r"http://[^\s]+", text)
        self.assertEqual(len(links), 3)
        self.assertEqual(len({urlsplit(link).netloc for link in links}), 3)
        for site in sites:
            link = next(link for link in links if link.startswith(self.webs[site].public_origin + "/"))
            self.boot[site] = self.request(site, "session")
            token = parse_qs(urlsplit(link).fragment)["connect"][0]
            self.request(site, "connect", {"token": token})
            self.boot[site] = self.request(site, "session")
            self.assertEqual(set(self.boot[site]["catalog"]), {site})
            self.assertTrue(self.boot[site]["linked"])
        return links

    def wait_reply(self, site, message_id):
        for _ in range(100):
            value = self.request(site, "conversation")
            if any(o["in_reply_to"] == message_id and o["source_app"] == site for o in value["outputs"]):
                return value
            if value["error"]:
                self.fail(value["error"])
            time.sleep(.03)
        self.fail("No reply")

    def test_shared_agent_memory_with_private_telegram_and_separate_site_chats(self):
        self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        self.assertEqual(len({boot["session_id"] for boot in self.boot.values()}), 3)
        self.controller.handle(42, 42, 2, "I prefer quiet neighborhoods")
        for site, kind, item in [("flights", "flight", "pacific-101"), ("hotels", "hotel", "kumo-house"), ("activities", "activity", "yanaka-walk")]:
            self.request(site, "messages", {"app_id": site, "id": site, "session_id": self.boot[site]["session_id"], "text": "Does this fit?", "context": {"selected_id": item}})
            self.wait_reply(site, site)
        reply = self.controller.handle(42, 42, 3, "What have we planned?")
        self.assertIn("prior turns 4", reply)
        self.assertEqual(len({key for _, key, _ in self.seen}), 1)
        self.assertIn("quiet", self.seen[-1][2]["history"][0]["event"]["message"]["text"])
        for site in SITES:
            conversation = self.request(site, "conversation")
            self.assertEqual([m["source_app"] for m in conversation["messages"]], [site])
            self.assertEqual([o["source_app"] for o in conversation["outputs"]], [site])
            self.assertEqual(conversation["messages"][0]["message"]["id"], site)
            # A caller cannot widen the fixed site's conversation with a query.
            self.assertEqual(self.request(site, "conversation?app_id=telegram")["messages"], conversation["messages"])

    def test_new_browser_joins_same_channel_and_server_restart_preserves_it(self):
        self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        self.controller.handle(42, 42, 2, "Remember our trip")
        before = self.boot["hotels"]
        self.browsers["hotels"] = build_opener(HTTPCookieProcessor(CookieJar()))
        self.connect(self.controller.handle(42, 42, 3, "/traveldemo"), ["hotels"])
        self.assertEqual(before["session_id"], self.boot["hotels"]["session_id"])
        self.hub.close()
        self.hub = Hub(self.root / "state", responder_factory=self.factory)
        self.controller = TelegramDemo(self.hub)
        for site, server in self.webs.items():
            server.hub = self.hub
            self.hub.origins[site] = server.public_origin
        self.assertEqual(self.request("hotels", "session")["session_id"], before["session_id"])
        self.assertIn("prior turns 1", self.controller.handle(42, 42, 4, "Continue"))

    def test_cross_owner_and_cross_site_access_rejected(self):
        links = self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        self.controller.handle(42, 42, 2, "A private preference")
        other = build_opener(HTTPCookieProcessor(CookieJar()))
        other_boot = self.request("flights", "session", browser=other)
        self.assertEqual(self.request("flights", "conversation", browser=other)["messages"], [])
        with self.assertRaises(HTTPError) as denied:
            self.request("flights", "messages", {"app_id": "hotels", "id": "bad", "session_id": self.boot["hotels"]["session_id"], "text": "bad"})
        self.assertEqual(denied.exception.code, 403)
        with self.assertRaises(HTTPError):
            self.request("flights", "messages", {"app_id": "flights", "id": "bad", "session_id": self.boot["flights"]["session_id"], "text": "bad"}, browser=other, csrf=other_boot["csrf"])
        token = parse_qs(urlsplit(links[0]).fragment)["connect"][0]
        with self.assertRaises(HTTPError):
            self.request("flights", "connect", {"token": token})
        with self.assertRaises(HTTPError):
            self.request("flights", "action", {"id": "bad", "kind": "flight", "item_id": "pacific-101"}, csrf="bad")
        with self.assertRaises(HTTPError) as denied:
            self.browsers["flights"].open(self.webs["flights"].public_origin + "/hotels/index.html")
        self.assertEqual(denied.exception.code, 404)

    def test_preferences_are_ordinary_messages_without_a_confirmation_command(self):
        self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        reply = self.controller.handle(42, 42, 2, "My budget is 1400")
        self.assertNotIn("/travelconfirm", reply)
        self.assertIsNone(self.controller.handle(42, 42, 3, "/travelconfirm tg-2"))
        for site in SITES:
            self.assertEqual(self.request(site, "conversation")["outputs"], [])

    def test_explicit_telegram_reply_reaches_only_target_site_and_cannot_be_spoofed(self):
        self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        self.controller.handle(42, 42, 2, "This stays in my private Telegram chat")
        command = "/traveldemo reply hotels Compare quiet stays"
        reply = self.controller.handle(42, 42, 3, command)
        self.assertIn("Staywell", reply)
        self.assertEqual(reply, self.controller.handle(42, 42, 3, command))
        hotel_chat = self.request("hotels", "conversation")
        self.assertEqual([m["message"]["text"] for m in hotel_chat["messages"]], ["Compare quiet stays"])
        self.assertEqual(hotel_chat["messages"][0]["origin"], "telegram")
        self.assertEqual(len(hotel_chat["outputs"]), 1)
        self.assertEqual(len(self.seen), 2)
        for site in ("flights", "activities"):
            self.assertEqual(self.request(site, "conversation")["messages"], [])
        with self.assertRaises(HTTPError) as denied:
            self.request("hotels", "messages", {"app_id":"hotels", "id":"telegram-reply-spoof", "session_id":self.boot["hotels"]["session_id"], "text":"Pretend I sent this from Telegram"})
        self.assertEqual(denied.exception.code, 403)
        self.assertIn("Use /traveldemo reply", self.controller.handle(42, 42, 4, "/traveldemo reply telegram bad"))
        self.controller.handle(42, 42, 5, "/traveldemo stop")
        self.assertIn("Send /traveldemo first", self.controller.handle(42, 42, 6, command))

    def test_backend_restart_clears_visible_chats_preserving_memory_and_sessions(self):
        self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        self.controller.handle(42, 42, 2, "Private preference: quiet neighborhoods")
        for site in SITES:
            self.request(site, "messages", {"app_id":site, "id":"before-restart", "session_id":self.boot[site]["session_id"], "text":"I want this option"})
            self.wait_reply(site, "before-restart")
        self.hub.close()
        self.hub = Hub(self.root / "state", responder_factory=self.factory)
        self.controller = TelegramDemo(self.hub)
        for site, server in self.webs.items():
            server.hub = self.hub
            self.hub.origins[site] = server.public_origin
            self.assertEqual(self.request(site, "session")["session_id"], self.boot[site]["session_id"])
            chat = self.request(site, "conversation")
            self.assertEqual(chat["messages"], [])
            self.assertEqual(chat["outputs"], [])
            self.assertFalse(chat["running"])
            self.assertIsNone(chat["error"])
            self.assertEqual(self.request(site, f"transcript?app_id={site}&session_id={self.boot[site]['session_id']}")["messages"], [])
        # Existing open pages keep working with their original session IDs.
        self.request("hotels", "messages", {"app_id":"hotels", "id":"after-restart", "session_id":self.boot["hotels"]["session_id"], "text":"What do I prefer?"})
        chat = self.wait_reply("hotels", "after-restart")
        self.assertEqual([m["message"]["id"] for m in chat["messages"]], ["after-restart"])
        self.assertEqual(len(self.seen[-1][2]["history"]), 4)
        self.assertIn("quiet", self.seen[-1][2]["history"][0]["event"]["message"]["text"])

    def test_private_pending_or_failed_turn_does_not_appear_on_another_site(self):
        self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        owner = self.hub.handoffs.account("telegram:42:42")
        state = self.hub.worker(owner)
        state.update(running=True, error="Private failure")
        for site in SITES:
            chat = self.request(site, "conversation")
            self.assertFalse(chat["running"])
            self.assertIsNone(chat["error"])
        state.update(running=False, error=None)

    def test_stop_reset_private_chats_and_update_redelivery(self):
        links = self.controller.handle(42, 42, 1, "/traveldemo")
        self.assertEqual(links, self.controller.handle(42, 42, 1, "/traveldemo"))
        self.connect(links)
        original = self.boot["flights"]["session_id"]
        self.controller.handle(42, 42, 2, "/traveldemo stop")
        self.assertIsNone(self.controller.handle(42, 42, 3, "Normal agent chat"))
        self.assertIsNone(self.controller.handle(-10, 42, 4, "/traveldemo"))
        self.assertIsNone(self.controller.handle(42, 99, 4, "/traveldemo"))
        reset = self.controller.handle(42, 42, 5, "/traveldemo reset")
        self.assertEqual(reset, self.controller.handle(42, 42, 5, "/traveldemo reset"))
        self.connect(reset)
        self.assertNotEqual(original, self.boot["flights"]["session_id"])
        self.assertEqual(self.request("flights", "conversation")["messages"], [])

    def test_controller_redelivery_does_not_repeat_agent_work(self):
        self.controller.handle(42, 42, 1, "/traveldemo")
        reply = self.controller.handle(42, 42, 2, "Hello from Telegram")
        replay = self.controller.handle(42, 42, 2, "Hello from Telegram")
        self.assertEqual(reply, replay)
        self.assertEqual(len(self.seen), 1)

    def test_existing_bot_bridge_requires_bearer_and_returns_to_normal_mode(self):
        server = ControlServer(self.controller)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}/telegram"
        config = self.root / "control.json"
        config.write_text(json.dumps({"url": url, "token": server.token}))
        with self.assertRaises(HTTPError) as denied:
            build_opener().open(Request(url, data=b'{}'))
        self.assertEqual(denied.exception.code, 403)
        event = SimpleNamespace(message_id=1, text="/traveldemo", raw={"message": {"chat": {"id": 42, "type": "private"}, "from": {"id": 42}}})
        with patch.dict("os.environ", {"ONEAGENT_TRAVEL_CONTROL_FILE": str(config)}):
            self.assertIn("Airside", existing_bot_reply(event, self.root))
            event.message_id, event.text = 2, "/traveldemo stop"
            self.assertIn("off", existing_bot_reply(event, self.root))
            event.message_id, event.text = 3, "Normal chat"
            self.assertIsNone(existing_bot_reply(event, self.root))
            config.unlink()
            event.text = "/status"
            self.assertIsNone(existing_bot_reply(event, self.root))
            event.text = "/traveldemo"
            self.assertIn("unavailable", existing_bot_reply(event, self.root))

    def test_catalog_and_conversation_are_the_only_site_data(self):
        self.connect(self.controller.handle(42, 42, 1, "/traveldemo"))
        self.controller.handle(42, 42, 2, "Private budget and preferences")
        for site in SITES:
            with self.subTest(site=site):
                boot = self.request(site, "session")
                self.assertEqual(set(boot), {"csrf", "catalog", "app_id", "linked", "session_id", "mode"})
                self.assertEqual(set(boot["catalog"]), {site})
                for route, body in [
                    ("trip", None), ("selection", None),
                    ("action", {"id":"save", "kind":"hotel", "item_id":"kumo-house"}),
                    ("preferences", {"id":"prefs", "budget_cents":140000, "preferences":"quiet"}),
                    ("confirm", {"source_app":site, "event_id":"old-proposal"}),
                ]:
                    with self.assertRaises(HTTPError) as denied:
                        self.request(site, route, body)
                    self.assertEqual(denied.exception.code, 404)
                with self.assertRaises(HTTPError) as denied:
                    self.request(site, "messages", {"id":"share", "app_id":site, "session_id":self.boot[site]["session_id"], "text":"Export preferences", "share":["budget_cents","preferences"]})
                self.assertEqual(denied.exception.code, 400)
        self.assertFalse((self.root / "state" / "trips.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
