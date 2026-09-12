from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PYTHON_CANDIDATES = ("python3.13", "python3.12", "python3.11", "python3", "python")


class OneAgentLauncherTests(unittest.TestCase):
    def test_launchers_probe_for_supported_python(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            root = _copy_launchers(bin_dir)
            log = bin_dir / "launch.log"
            _write_fake_pythons(bin_dir)
            env = _launcher_env(bin_dir, log, supported={"python3.11"})

            cases = [
                ("bin/oneagent", ["doctor"], "python3.11 -m oneagent doctor"),
                ("bin/oneagent-daemon", ["status"], "python3.11 -m oneagent.operations.daemon status"),
                ("bin/oneagent-agent", [], "python3.11 -m oneagent.agent"),
            ]

            for script, args, expected in cases:
                with self.subTest(script=script):
                    log.write_text("", encoding="utf-8")

                    result = subprocess.run(
                        [str(root / script), *args],
                        cwd="/",
                        env=env,
                        text=True,
                        capture_output=True,
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(expected, log.read_text(encoding="utf-8"))

    def test_oneagent_python_overrides_probe_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            root = _copy_launchers(bin_dir, venv=True)
            log = bin_dir / "launch.log"
            custom_python = bin_dir / "custom-python"
            _write_fake_pythons(bin_dir, extra=(custom_python.name,))
            env = _launcher_env(bin_dir, log, supported={custom_python.name, "python", "python3.11"})
            env["ONEAGENT_PYTHON"] = str(custom_python)

            result = subprocess.run(
                [str(root / "bin/oneagent"), "doctor"],
                cwd="/",
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log.read_text(encoding="utf-8"), "custom-python -m oneagent doctor\n")

    def test_unsupported_oneagent_python_fails_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            root = _copy_launchers(bin_dir, venv=True)
            log = bin_dir / "launch.log"
            _write_fake_pythons(bin_dir)
            env = _launcher_env(bin_dir, log, supported={"python", "python3.11"})
            env["ONEAGENT_PYTHON"] = str(bin_dir / "python3")

            result = subprocess.run(
                [str(root / "bin/oneagent"), "doctor"],
                cwd="/",
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ONEAGENT_PYTHON points to an unsupported interpreter", result.stderr)
            self.assertFalse(log.exists())

    def test_launchers_prefer_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            root = _copy_launchers(bin_dir, venv=True)
            log = bin_dir / "launch.log"
            _write_fake_pythons(bin_dir)
            env = _launcher_env(bin_dir, log, supported={"python", "python3.13"})
            for script in ("oneagent", "oneagent-agent", "oneagent-daemon"):
                with self.subTest(script=script):
                    log.write_text("", encoding="utf-8")
                    result = subprocess.run(
                        [str(root / "bin" / script)],
                        cwd="/", env=env, text=True, capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(log.read_text(encoding="utf-8").startswith("python -m "))


def _copy_launchers(directory: Path, *, venv: bool = False) -> Path:
    root = directory / "project"
    shutil.copytree(ROOT / "bin", root / "bin")
    if venv:
        venv_bin = root / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        _write_fake_pythons(venv_bin)
    return root


def _launcher_env(bin_dir: Path, log: Path, *, supported: set[str]) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("ONEAGENT_PYTHON", None)
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    env["ONEAGENT_TEST_LAUNCH_LOG"] = str(log)
    env["ONEAGENT_TEST_SUPPORTED_PYTHONS"] = " ".join(sorted(supported))
    return env


def _write_fake_pythons(bin_dir: Path, *, extra: tuple[str, ...] = ()) -> None:
    for name in (*PYTHON_CANDIDATES, *extra):
        path = bin_dir / name
        path.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    'name="${0##*/}"',
                    'if [[ "${1:-}" == "-c" ]]; then',
                    '  case " ${ONEAGENT_TEST_SUPPORTED_PYTHONS:-} " in',
                    '    *" $name "*) exit 0 ;;',
                    "    *) exit 1 ;;",
                    "  esac",
                    "fi",
                    'printf "%s %s\\n" "$name" "$*" >> "$ONEAGENT_TEST_LAUNCH_LOG"',
                    "exit 0",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
