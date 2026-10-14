import asyncio
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from tsec_benchmark import DuplicateSubmit, InvalidState, TSecConnectionError
from tsec_benchmark.models import Challenge, CloseResult, StartResult, SubmitResult

from tsec_agent.benchmark import (
    BenchmarkRunner,
    ChallengeTools,
    CleanupError,
    PlatformEnded,
    PlatformError,
    platform_error,
)
from tsec_agent.runtime import AgentExecutionError, Budget, BudgetExhausted


def challenge(code="first", completed=False):
    return Challenge(
        code, "easy", 1, 100, 1, int(completed), completed, "Assigned task"
    )


class FakeClient:
    def __init__(self, challenges=None):
        self.challenges = [challenge()] if challenges is None else challenges
        self.events = []
        self.start_error = None
        self.close_error = None

    async def list_challenges(self):
        return list(self.challenges)

    async def start_challenge(self, code):
        self.events.append(("start", code))
        if self.start_error:
            raise self.start_error
        return StartResult(code, ["127.0.0.1:8080"])

    async def submit_flag(self, code, flag):
        self.events.append(("submit", code))
        for index, ch in enumerate(self.challenges):
            if ch.unique_code == code:
                if ch.is_completed:
                    raise DuplicateSubmit("Already submitted")
                self.challenges[index] = replace(
                    ch, is_completed=True, correct_flag_count=1
                )
        return SubmitResult(True, 100, 100, 1, 1, 0)

    async def close_challenge(self, code):
        self.events.append(("close", code))
        if self.close_error:
            raise self.close_error
        return CloseResult(code, True)


class FakeAgent:
    def __init__(self, action=None):
        self.action = action
        self.workspaces = []

    async def run(self, prompt, workspace, budget, tools):
        self.workspaces.append(workspace)
        budget.requests += 1
        if self.action:
            return await self.action(tools)
        await tools[0]("candidate")
        return "Task complete"


class BenchmarkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def runner(self, client, agent=None, **kwargs):
        return BenchmarkRunner(
            client, agent or FakeAgent(), self.root, Budget(), **kwargs
        )

    async def test_completes_and_skips_completed_challenges(self):
        client = FakeClient([challenge("done", True), challenge("../../unsafe")])
        agent = FakeAgent()
        result = await self.runner(client, agent).run()
        self.assertEqual(result["stop_reason"], "all_completed")
        self.assertEqual(result["completed_challenges"], 2)
        self.assertEqual(
            client.events,
            [
                ("start", "../../unsafe"),
                ("submit", "../../unsafe"),
                ("close", "../../unsafe"),
            ],
        )
        self.assertEqual(agent.workspaces[0].parent, self.root)

    async def test_solver_claim_does_not_count_as_success(self):
        async def claim(tools):
            return "Solved!"

        result = await self.runner(FakeClient(), FakeAgent(claim)).run()
        self.assertEqual(result["completed_challenges"], 0)
        self.assertEqual(result["stop_reason"], "selected_pass_complete")

    async def test_solver_failure_cleans_up_and_continues(self):
        async def fail(tools):
            raise AgentExecutionError("Failed")

        client = FakeClient([challenge("one"), challenge("two")])
        result = await self.runner(client, FakeAgent(fail)).run()
        self.assertEqual(len(result["outcomes"]), 2)
        self.assertEqual(
            [e for e in client.events if e[0] == "close"],
            [("close", "one"), ("close", "two")],
        )

    async def test_uncertain_start_is_closed_without_retry(self):
        client = FakeClient()
        client.start_error = TSecConnectionError("Lost response with sensitive details")
        with self.assertRaises(PlatformError):
            await self.runner(client).run()
        self.assertEqual(client.events, [("start", "first"), ("close", "first")])

    async def test_cleanup_failure_stops_scheduling(self):
        client = FakeClient([challenge("one"), challenge("two")])
        client.close_error = TSecConnectionError("Lost response")
        with self.assertRaises(CleanupError):
            await self.runner(client).run()
        self.assertNotIn(("start", "two"), client.events)

    async def test_challenge_timeout_closes_target(self):
        async def wait(tools):
            await asyncio.Event().wait()

        client = FakeClient()
        result = await self.runner(
            client, FakeAgent(wait), challenge_timeout=0.01
        ).run()
        self.assertEqual(result["outcomes"][0]["status"], "timeout")
        self.assertIn(("close", "first"), client.events)

    async def test_cancellation_closes_target(self):
        ready = asyncio.Event()

        async def wait(tools):
            ready.set()
            await asyncio.Event().wait()

        client = FakeClient()
        task = asyncio.create_task(self.runner(client, FakeAgent(wait)).run())
        await ready.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertIn(("close", "first"), client.events)

    async def test_budget_is_shared_between_challenges(self):
        client = FakeClient([challenge("one"), challenge("two")])
        runner = self.runner(client)
        runner.budget = Budget(request_limit=1)
        with self.assertRaises(BudgetExhausted):
            await runner.run()
        self.assertNotIn(("start", "two"), client.events)

    async def test_challenge_limit(self):
        client = FakeClient([challenge("one"), challenge("two")])
        result = await self.runner(client, max_challenges=1).run()
        self.assertEqual(result["stop_reason"], "challenge_limit")
        self.assertEqual(len(result["outcomes"]), 1)

    async def test_hint_is_not_exposed_by_default_and_duplicate_is_safe(self):
        tools = ChallengeTools(FakeClient(), "first")
        self.assertEqual(
            [f.__name__ for f in tools.functions()], ["submit_flag", "get_progress"]
        )
        await tools.submit_flag("secret-flag")
        result = await tools.submit_flag("secret-flag")
        self.assertEqual(result, {"already_submitted": True})
        self.assertNotIn("secret-flag", str(result))

    def test_invalid_state_is_classified_by_context(self):
        self.assertNotIsInstance(
            platform_error(InvalidState("max active reached")), PlatformEnded
        )
        self.assertIsInstance(
            platform_error(InvalidState("task has ended")), PlatformEnded
        )
