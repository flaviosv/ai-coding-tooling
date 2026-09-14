import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import session_metrics as sm


class IsFullSuiteRunTest(unittest.TestCase):
    def assertFull(self, *commands):
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(sm.is_full_suite_run(command))

    def assertScoped(self, *commands):
        for command in commands:
            with self.subTest(command=command):
                self.assertFalse(sm.is_full_suite_run(command))

    def test_npm(self):
        self.assertFull("npm test", "npm run test -- --run 2>&1 | tail -40", "pnpm test --silent")
        self.assertScoped(
            "npm test -- src/a.test.ts",
            "npm test -- AppShell.test 2>&1 | head -100",
            "npm test -- WeekView",
            "npm run test -- --run src/a.test.ts",
            'npm test -- -t "renders header"',
        )

    def test_pytest(self):
        self.assertFull("pytest", "pytest -q", 'pytest -m "not integration"', "uv run pytest -n auto --cov=src/app")
        self.assertScoped(
            "pytest tests/test_x.py",
            "pytest -q test_x.py",
            "python -m pytest tests/unit/",
            "pytest -k test_login",
        )

    def test_go(self):
        self.assertFull("go test ./...", "go test ./... -v 2>&1 | tail -40")
        self.assertScoped("go test ./pkg/foo", "go test ./... -run TestLogin")

    def test_phpunit(self):
        self.assertFull("phpunit", "phpunit --testdox")
        self.assertScoped("phpunit tests/Unit/FooTest.php", "phpunit --testdox FooTest.php", "phpunit --filter testLogin")


if __name__ == "__main__":
    unittest.main()
