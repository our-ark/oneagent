"""Include the bundled Telegram provider's rendering and transport regressions."""

from pathlib import Path
import unittest


def load_tests(loader, tests, pattern):
    provider_tests = Path(__file__).resolve().parents[1] / "libraries" / "telegram" / "tests"
    return unittest.TestLoader().discover(str(provider_tests))
