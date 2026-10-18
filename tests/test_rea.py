import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastmcp import FastMCP
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from tsec_agent.config import ConfigurationError
from tsec_agent.rea import capability
from tsec_agent.runtime import Budget, CyberAgent


class ReaTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "rea-package"
        skill = self.package / "skills/reverse-engineer-anything/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: reverse-engineer-anything\n"
            "description: Inspect packaged artifacts with REA.\n---\n"
            "# REA fixture\nRead references/details.md for evidence rules.\n"
        )
        reference = skill.parent / "references/details.md"
        reference.parent.mkdir()
        reference.write_text("Fixture evidence rules")
        entry = self.package / "scripts/rea.mjs"
        entry.parent.mkdir()
        entry.touch()

    def test_invalid_installation_fails_before_model_execution(self):
        with self.assertRaises(ConfigurationError):
            CyberAgent(
                FunctionModel(lambda messages, info: None),
                project=self.root,
                rea_root=self.root / "missing",
            )

    def test_transport_environment_excludes_credentials_and_disables_keep_alive(self):
        with patch.dict(
            os.environ,
            {
                "LLM_API_KEY": "model-fixture",
                "BENCHMARK_TOKEN": "benchmark-fixture",
                "UNRELATED_SECRET": "another-fixture",
                "JAVA_HOME": "/fixture/jdk",
                "GHIDRA_INSTALL_DIR": "/fixture/ghidra",
                "REA_ANALYSIS_PROVIDER": "ghidra",
            },
        ):
            transport = capability(self.package, self.root).local.client.transport
        self.assertFalse(transport.keep_alive)
        self.assertEqual(transport.args, [str(self.package / "scripts/rea.mjs"), "mcp"])
        self.assertEqual(transport.cwd, str(self.root.resolve()))
        self.assertEqual(transport.env["JAVA_HOME"], "/fixture/jdk")
        self.assertEqual(transport.env["REA_ANALYSIS_PROVIDER"], "ghidra")
        for key in ("LLM_API_KEY", "BENCHMARK_TOKEN", "UNRELATED_SECRET"):
            self.assertNotIn(key, transport.env)

    async def test_skill_reference_mount_and_deferred_mcp_use_native_harness(self):
        server = FastMCP("rea-fixture")

        @server.tool
        def fixture_probe() -> str:
            """Return a harmless integration observation."""
            return "REA fixture connected"

        async def respond(messages, info):
            self.assertIn("reverse-engineer-anything", str(info.instructions))
            results = [
                p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
            ]
            tools = {tool.name for tool in info.function_tools}
            if not results:
                self.assertIn("load_capability", tools)
                self.assertNotIn("fixture_probe", tools)
                call = (
                    "view",
                    {
                        "file_path": "/environment/rea/skills/reverse-engineer-anything/references/details.md"
                    },
                )
            elif len(results) == 1:
                self.assertIn("Fixture evidence rules", str(results[-1].content))
                call = (
                    "write",
                    {
                        "file_path": "/environment/rea/forbidden.txt",
                        "content": "blocked",
                    },
                )
            elif len(results) == 2:
                self.assertFalse(results[-1].content["ok"])
                call = ("load_capability", {"id": "rea"})
            elif len(results) == 3:
                call = (
                    next(name for name in tools if name.endswith("fixture_probe")),
                    {},
                )
            else:
                self.assertIn("REA fixture connected", str(results[-1].content))
                yield "REA verified"
                return
            yield {0: DeltaToolCall(name=call[0], json_args=json.dumps(call[1]))}

        with (
            patch("tsec_agent.rea.shutil.which", return_value=sys.executable),
            patch("tsec_agent.rea.StdioTransport", return_value=server),
        ):
            agent = CyberAgent(
                FunctionModel(stream_function=respond),
                project=self.root,
                rea_root=self.package,
            )
            result = await agent.run(
                "Verify REA integration offline",
                self.root / "workspace",
                Budget(request_limit=6),
            )
        self.assertEqual(result, "REA verified")
        self.assertFalse((self.package / "forbidden.txt").exists())
