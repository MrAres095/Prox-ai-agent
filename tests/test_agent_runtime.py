import os
import tempfile
import unittest

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AGENT_WORKSPACE"] = self.tmp.name
        import importlib, agent_runtime
        self.runtime = importlib.reload(agent_runtime)

    def tearDown(self):
        self.tmp.cleanup()

    def test_allowed_command_runs(self):
        result = self.runtime.run_workspace_command('python3 -c "print(42)"')
        self.assertEqual(result["returncode"], 0)
        self.assertIn("42", result["output"])

    def test_shell_chaining_and_absolute_paths_blocked(self):
        for command in ("ls; whoami", "cat /etc/passwd"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.runtime.run_workspace_command(command)

    def test_file_read_write_and_traversal(self):
        self.runtime.write_workspace_file("subdir/example.txt", "hello")
        self.assertEqual(self.runtime.read_workspace_file("subdir/example.txt")["content"], "hello")
        with self.assertRaises(ValueError):
            self.runtime.read_workspace_file("../outside.txt")

    def test_unknown_tool_rejected(self):
        self.assertIn("error", self.runtime.execute_tool("delete_everything", "{}"))

if __name__ == "__main__":
    unittest.main()
