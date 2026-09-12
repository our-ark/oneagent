"""Run: python examples/notes/roundtrip.py [--real-model]

Default uses a clearly labeled transport fixture. --real-model uses OneAgent's
configured runtime; it is not a canned assistant. No credentials are committed.
"""
import argparse
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from oneagent.collaboration import AgentState, AppClient, AppServer, CollaborationService, MessageStore, OneAgentResponder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-model", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="oneagent-notes-") as directory:
        root = Path(directory)
        store = MessageStore(root / "notes.sqlite", "notes")
        server = AppServer(("127.0.0.1", 0), store, {"local-example-only": "demo-user"})
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            session = store.session("demo-user")["session_id"]
            store.message("demo-user", {"id": "hello", "session_id": session,
                "text": "Explain the selected sentence in simpler terms.",
                "context": {"document_id": "note-1", "selected_text": "Application boundaries should not end a conversation."}})
            app = AppClient("notes", f"http://127.0.0.1:{server.server_port}", "local-example-only")
            respond = OneAgentResponder(root / "agent") if args.real_model else lambda payload, session_key: {
                "text": "[Transport fixture] Received: " + payload["current"]["context"]["selected_text"]}
            service = CollaborationService([app], AgentState(root / "agent.sqlite", "demo-user"), respond)
            service.process_once()
            print(store.transcript("demo-user", session)["outputs"][0]["text"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
