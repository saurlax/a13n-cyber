import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from a13n_harness import AgentSpec
from a13n_harness.errors import DefinitionError
from fastmcp import FastMCP
from pydantic_ai.capabilities import MCP
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from tsec_agent.runtime import (
    AgentConfiguration,
    AgentExecutionError,
    Budget,
    CyberAgent,
)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_agent_file_rejects_unknown_fields_and_accepts_native_mcp(self):
        with self.assertRaises(ValueError):
            AgentConfiguration.from_dict({"instruction_typo": "ignored"})
        spec = AgentConfiguration.from_dict(
            {
                "capabilities": [
                    {
                        "MCP": {
                            "url": "https://mcp.example.com/mcp",
                            "id": "knowledge",
                            "local": True,
                        }
                    }
                ]
            }
        )
        self.assertEqual(spec.capabilities[0].name, "MCP")

    async def test_real_harness_reads_file_then_calls_bound_tool(self):
        (self.root / "evidence.txt").write_text("verified-evidence", encoding="utf-8")
        submissions = []

        async def submit_flag(flag: str) -> dict:
            """Submit the candidate for this task."""
            submissions.append(flag)
            return {"correct": True}

        async def respond(messages, info):
            results = [
                p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
            ]
            if not results:
                self.assertIn("shell_exec", [t.name for t in info.function_tools])
                yield {
                    0: DeltaToolCall(
                        name="view",
                        json_args=json.dumps({"file_path": "/workspace/evidence.txt"}),
                    )
                }
            elif not any(p.tool_name == "submit_flag" for p in results):
                self.assertIn("verified-evidence", str(results[-1].content))
                yield {
                    0: DeltaToolCall(
                        name="submit_flag", json_args='{"flag":"candidate"}'
                    )
                }
            else:
                yield "Platform confirmed"

        agent = CyberAgent(FunctionModel(stream_function=respond), project=self.root)
        budget = Budget()
        result = await agent.run(
            "Verify evidence and submit", self.root, budget, (submit_flag,)
        )
        self.assertEqual(result, "Platform confirmed")
        self.assertEqual(submissions, ["candidate"])
        self.assertEqual(budget.requests, 3)
        self.assertGreater(budget.tokens, 0)

    async def test_skills_from_project_are_available_in_challenge_workspace(self):
        package = self.root / ".agents" / "skills" / "analysis"
        package.mkdir(parents=True)
        (package / "SKILL.md").write_text(
            "---\nname: analysis\ndescription: Evidence analysis workflow.\n---\nRead evidence carefully.\n",
            encoding="utf-8",
        )

        async def respond(messages, info):
            self.assertIn("analysis", str(info.instructions))
            self.assertIn("/environment/project/.agents/skills", str(info.instructions))
            yield "Skill available"

        agent = CyberAgent(FunctionModel(stream_function=respond), project=self.root)
        result = await agent.run("Inspect skills", self.root / "challenge", Budget())
        self.assertEqual(result, "Skill available")

    async def test_builtin_skill_is_discovered_readable_and_file_only(self):
        async def respond(messages, info):
            self.assertIn("a13n-toolkit", str(info.instructions))
            results = [
                p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
            ]
            if not results:
                call = (
                    "view",
                    {"file_path": "/environment/builtin/skills/a13n-toolkit/SKILL.md"},
                )
            elif len(results) == 1:
                self.assertIn("Packaged Toolkit", str(results[-1].content))
                call = (
                    "write",
                    {
                        "file_path": "/environment/builtin/write-check.txt",
                        "content": "not allowed",
                    },
                )
            else:
                self.assertIsInstance(results[-1].content, dict)
                self.assertFalse(results[-1].content["ok"])
                yield "Built-in skill verified"
                return
            yield {0: DeltaToolCall(name=call[0], json_args=json.dumps(call[1]))}

        for workspace in (self.root, self.root / "challenge"):
            with self.subTest(workspace=workspace):
                result = await CyberAgent(
                    FunctionModel(stream_function=respond), project=self.root
                ).run("Check packaged skills", workspace, Budget())
                self.assertEqual(result, "Built-in skill verified")

    async def test_project_cannot_silently_replace_a_builtin_skill(self):
        package = self.root / ".agents" / "skills" / "a13n-toolkit"
        package.mkdir(parents=True)
        (package / "SKILL.md").write_text(
            "---\nname: a13n-toolkit\ndescription: Conflicting project skill.\n---\nConflict.\n",
            encoding="utf-8",
        )
        calls = []

        async def respond(messages, info):
            calls.append(True)
            yield "Should not run"

        with self.assertRaises(DefinitionError) as failure:
            await CyberAgent(
                FunctionModel(stream_function=respond), project=self.root
            ).run("Check skill identity conflicts", self.root, Budget())
        self.assertEqual(failure.exception.code, "skill_catalog_ambiguous")
        self.assertEqual(calls, [])

    async def test_usage_limit_stops_real_loop_and_accounts_for_requests(self):
        async def again() -> str:
            """Return another observation."""
            return "Continue"

        async def respond(messages, info):
            yield {0: DeltaToolCall(name="again", json_args="{}")}

        agent = CyberAgent(FunctionModel(stream_function=respond), project=self.root)
        budget = Budget(request_limit=2)
        with self.assertRaises(AgentExecutionError):
            await agent.run("Keep observing", self.root, budget, (again,))
        self.assertEqual(budget.requests, 2)

    async def test_shell_executes_in_workspace_without_model_credentials(self):
        async def respond(messages, info):
            results = [
                p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
            ]
            if results:
                self.assertIn("shell-ok", str(results[-1].content))
                yield "Shell verified"
            else:
                yield {
                    0: DeltaToolCall(
                        name="shell_exec", json_args='{"command":"echo shell-ok"}'
                    )
                }

        agent = CyberAgent(FunctionModel(stream_function=respond), project=self.root)
        self.assertEqual(
            await agent.run("Check shell", self.root, Budget()), "Shell verified"
        )

    def test_agent_spec_cannot_override_model(self):
        async def respond(messages, info):
            yield "unused"

        with self.assertRaises(ValueError):
            CyberAgent(
                FunctionModel(stream_function=respond),
                project=self.root,
                spec=AgentSpec(model="openai:other"),
            )

    async def test_native_mcp_capability_uses_the_same_harness_loop(self):
        server = FastMCP("local-calculator")

        @server.tool
        def add(a: int, b: int) -> int:
            """Add two integers."""
            return a + b

        async def respond(messages, info):
            results = [
                p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
            ]
            if results:
                self.assertIn("8", str(results[-1].content))
                yield "MCP verified"
            else:
                name = next(
                    t.name for t in info.function_tools if t.name.endswith("add")
                )
                yield {0: DeltaToolCall(name=name, json_args='{"a":3,"b":5}')}

        agent = CyberAgent(
            FunctionModel(stream_function=respond),
            project=self.root,
            capabilities=(MCP(id="calculator", local=server),),
        )
        self.assertEqual(
            await agent.run("Add three and five", self.root, Budget()), "MCP verified"
        )
