from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from oneagent.collaboration import AgentState, AppClient, AppServer, CollaborationService, MessageStore, Tool, ToolRegistry


class CollaborationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.apps = []
        self.stores = []
        for name in ["notes", "board"]:
            store = MessageStore(self.root / f"{name}.sqlite", name, shared_fields=["language"])
            server = AppServer(("127.0.0.1", 0), store, {"secret": "alice", "other": "bob"})
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            self.apps.append(AppClient(name, f"http://127.0.0.1:{server.server_port}", "secret"))
            self.stores.append(store)
        self.state = AgentState(self.root / "agent.sqlite", "alice-conversation")

    def message(self, index, text="Explain this", **kwargs):
        store = self.stores[index]
        session = store.session("alice")["session_id"]
        event = store.message("alice", dict(id=kwargs.pop("id", "m1"), session_id=session, text=text,
                                            context=kwargs.pop("context", {"selected_text": "Hello"}), **kwargs))
        return session, event

    def test_cross_app_history_and_source_routing(self):
        a, _ = self.message(0, "My preferred language is Spanish")
        b, _ = self.message(1, "Explain this paragraph")
        calls = []
        def respond(payload, session):
            calls.append((payload, session))
            return {"text": "First" if not payload["history"] else "Spanish explanation"}
        service = CollaborationService(self.apps, self.state, respond)
        self.assertEqual(service.process_once(), 2)
        self.assertEqual([key for _, key in calls], ["alice-conversation"] * 2)
        self.assertIn("Spanish", calls[1][0]["history"][0]["event"]["message"]["text"])
        self.assertEqual(self.stores[0].transcript("alice", a)["outputs"][0]["text"], "First")
        self.assertEqual(self.stores[1].transcript("alice", b)["outputs"][0]["text"], "Spanish explanation")
        self.assertEqual(service.process_once(), 0)

    def test_context_is_frozen_and_duplicate_ids_conflict(self):
        context = {"selected": {"id": "original"}}
        session, event = self.message(0, context=context)
        context["selected"]["id"] = "later"
        self.assertEqual(self.apps[0].events()["events"][0]["context"]["selected"]["id"], "original")
        body = dict(id="m1", session_id=session, text="Explain this", context=event["context"])
        self.assertEqual(self.stores[0].message("alice", body)["cursor"], event["cursor"])
        with self.assertRaises(ValueError):
            self.stores[0].message("alice", dict(body, text="changed"))

    def test_account_isolation(self):
        session, _ = self.message(0)
        self.assertEqual(self.stores[0].events("bob")["events"], [])
        with self.assertRaises(PermissionError):
            self.stores[0].transcript("bob", session)
        with self.assertRaises(PermissionError):
            self.stores[0].message("bob", dict(id="stolen", session_id=session, text="x", context={}))
        other = AppClient("notes", self.apps[0].base_url, "other")
        self.assertEqual(other.events()["events"], [])
        with self.assertRaises(ConnectionError):
            AppClient("notes", self.apps[0].base_url, "invalid").events()

    def test_reply_must_match_session_and_disclosure(self):
        session, _ = self.message(0)
        wrong = self.stores[0].session("alice")["session_id"]
        reply = dict(id="o1", in_reply_to="m1", text="answer")
        with self.assertRaises(PermissionError):
            self.stores[0].output("alice", wrong, reply)
        with self.assertRaises(PermissionError):
            self.stores[0].output("alice", session, dict(reply, shared_context={"language": "es"}))
        self.stores[0].output("alice", session, reply)
        self.stores[0].output("alice", session, reply)
        with self.assertRaises(ValueError):
            self.stores[0].output("alice", session, dict(reply, text="changed"))

    def test_authorized_bidirectional_context(self):
        session, _ = self.message(0, share=["language"])
        service = CollaborationService(self.apps, self.state, lambda *_: {"text": "Hola", "shared_context": {"language": "es"}})
        service.process_once()
        self.assertEqual(self.stores[0].transcript("alice", session)["outputs"][0]["shared_context"], {"language": "es"})

    def test_runtime_disclosure_rejected_before_delivery(self):
        self.message(0)
        service = CollaborationService(self.apps, self.state, lambda *_: {"text": "answer", "shared_context": {"secret": "x"}})
        with self.assertRaises(PermissionError):
            service.process_once()
        self.assertEqual(self.state.history(), [])

    def test_restart_after_ambiguous_delivery_reuses_reply(self):
        session, _ = self.message(0)
        calls = []
        service = CollaborationService(self.apps, self.state, lambda *_: calls.append(1) or "answer")
        original = self.apps[0].output
        def uncertain(*args):
            original(*args)
            raise ConnectionError("lost response")
        with patch.object(self.apps[0], "output", uncertain):
            with self.assertRaises(ConnectionError):
                service.process_once()
        restarted = CollaborationService(self.apps, AgentState(self.state.path, "alice-conversation"), lambda *_: self.fail("reasoning repeated"))
        self.assertEqual(restarted.process_once(), 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.stores[0].transcript("alice", session)["outputs"]), 1)
        with self.assertRaises(ValueError):
            AgentState(self.state.path, "bob-conversation")

    def test_generic_tool_requires_explicit_authorization(self):
        tools = ToolRegistry()
        def validate(args):
            if set(args) != {"text"} or not isinstance(args["text"], str):
                raise ValueError("Invalid note")
        tools.register(Tool("notes.save", "Save a note", {"type": "object"}, lambda owner, args, key: {"owner": owner, "note": args["text"], "key": key}, validate, True))
        with self.assertRaises(PermissionError):
            tools.invoke("notes.save", {"text": "x"}, owner="alice", request_id="r1")
        result = tools.invoke("notes.save", {"text": "x"}, owner="alice", request_id="r1", authorize=lambda *_: True)
        self.assertEqual(result["note"], "x")
        with self.assertRaises(ValueError):
            tools.invoke("notes.save", {"wrong": True}, owner="alice", request_id="r2", authorize=lambda *_: True)

    def test_no_plaintext_remote_credentials(self):
        with self.assertRaises(ValueError):
            AppClient("notes", "http://example.com", "secret")
        self.assertNotIn("secret", repr(self.apps[0]))


if __name__ == "__main__":
    unittest.main()
