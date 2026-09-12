from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch


from oneagent.operations import daemon
from oneagent.migration import AgentMigrationError
from oneagent.providers.contracts import ServiceProviderError


class _Service:
    name = "test-service"
    provider_kind = "service"

    def __init__(self) -> None:
        self.calls = []

    def install(self, root=None):
        self.calls.append(("install", root))
        return "installed"

    def uninstall(self, root=None):
        self.calls.append(("uninstall", root))
        return "uninstalled"

    def start(self, root=None):
        self.calls.append(("start", root))
        return "started"

    def stop(self, root=None, *, allow_missing=False):
        self.calls.append(("stop", root, allow_missing))
        return "stopped"

    def restart(self, root=None):
        self.calls.append(("restart", root))
        return "restarted"

    def status(self, root=None):
        return "running"

    def logs(self, root=None, *, lines=80):
        return f"logs:{lines}"

    def doctor(self, root=None):
        return "Service provider: test-service\n- service: ok"

    def manifest(self, root=None):
        return "service manifest"


class OneagentDaemonTests(unittest.TestCase):
    def test_install_validates_chat_and_delegates_to_service(self) -> None:
        service = _Service()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("oneagent.operations.daemon._require_daemon_config") as require_config,
                patch("oneagent.operations.daemon._service", return_value=service),
            ):
                result = daemon.install(root)

        self.assertEqual(result, "installed")
        require_config.assert_called_once_with(root.resolve())
        self.assertEqual(service.calls, [("install", root.resolve())])

    def test_restart_validates_chat_and_uses_atomic_provider_restart(self) -> None:
        service = _Service()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("oneagent.operations.daemon._require_daemon_config"),
                patch("oneagent.operations.daemon._service", return_value=service),
            ):
                result = daemon.restart(root)

        self.assertEqual(result, "restarted")
        self.assertEqual(service.calls, [("restart", root.resolve())])

    def test_dispatch_routes_status_logs_and_manifest(self) -> None:
        service = _Service()
        with patch("oneagent.operations.daemon._service", return_value=service):
            self.assertEqual(daemon.dispatch("status"), "running")
            self.assertEqual(daemon.dispatch("logs", lines=12), "logs:12")
            self.assertEqual(daemon.dispatch("manifest"), "service manifest")

    def test_doctor_combines_chat_and_service_readiness(self) -> None:
        service = _Service()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("oneagent.operations.daemon._has_daemon_config", return_value=True),
                patch("oneagent.operations.daemon.provider_name", return_value="test-chat"),
                patch("oneagent.operations.daemon._service", return_value=service),
            ):
                result = daemon.doctor(root)

        self.assertIn("Oneagent service doctor:", result)
        self.assertIn("- config: ok", result)
        self.assertIn("Service provider: test-service", result)

    @patch("builtins.print")
    @patch("oneagent.operations.daemon.dispatch", side_effect=ServiceProviderError("service unavailable"))
    def test_main_reports_service_provider_errors(self, _dispatch: MagicMock, print_: MagicMock) -> None:
        with self.assertRaises(SystemExit):
            daemon.main(["status"])

        print_.assert_called_once_with("service unavailable")

    def test_start_requires_configured_chat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("oneagent.operations.daemon._has_daemon_config", return_value=False):
                with self.assertRaisesRegex(daemon.DaemonError, "Configure the selected chat provider"):
                    daemon.start(root)

    def test_start_and_restart_reject_an_exported_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "oneagent.operations.daemon.assert_runtime_start_allowed",
                side_effect=AgentMigrationError("source is fenced"),
            ):
                with self.assertRaisesRegex(AgentMigrationError, "source is fenced"):
                    daemon.start(root)
                with self.assertRaisesRegex(AgentMigrationError, "source is fenced"):
                    daemon.restart(root)


if __name__ == "__main__":
    unittest.main()
