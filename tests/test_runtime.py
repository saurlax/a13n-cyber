import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from a13n_harness import AgentSpec
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
