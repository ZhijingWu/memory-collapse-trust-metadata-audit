"""ExpeL EDIT trust ablation; stdlib only, no model calls or live environment.

Run: python3 tests/test_memory_expel.py
The private namespace loads the real ExpeL modules without importing unrelated
memory methods (whose package auto-discovery needs optional numpy/ML libraries).
Test artifacts stay under outputs/; no existing files are removed.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__import__("os").environ["AUDIT_UPSTREAM"])
MEMORY = ROOT / "agentgym/agentenv/agentenv/memory"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


for name, path in [
    ("_expel_test", MEMORY.parent),
    ("_expel_test.memory", MEMORY),
    ("_expel_test.memory.methods", MEMORY / "methods"),
    ("_expel_test.memory.methods.expel", MEMORY / "methods/expel"),
]:
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules[name] = package

base = load_module("_expel_test.memory.base", MEMORY / "base.py")
load_module("_expel_test.memory.registry", MEMORY / "registry.py")
load_module("_expel_test.memory.pool", MEMORY / "pool.py")
rules = load_module("_expel_test.memory.methods.expel.rules", MEMORY / "methods/expel/rules.py")
core = load_module("_expel_test.memory.methods.expel.core", MEMORY / "methods/expel/core.py")


class RuleTests(unittest.TestCase):
    def test_inherit_edit(self):
        self.assertEqual(
            rules.update_rules([("old rule", 7)], [("EDIT 1", "new rule")],
                               expel_edit_count_policy="inherit"),
            [("new rule", 8)],
        )

    def test_reset_edit_uses_add_initial_count(self):
        added = rules.update_rules([], [("ADD", "new rule")])
        self.assertEqual(added, [("new rule", rules.ADD_INITIAL_COUNT)])
        self.assertEqual(
            rules.update_rules([("old rule", 7)], [("EDIT 1", "new rule")],
                               expel_edit_count_policy="reset"), added,
        )

    def test_default_preserves_original_mixed_operation_result(self):
        initial = [("alpha", 7), ("beta", 4), ("gamma", 1)]
        ops = [("ADD", "delta"), ("EDIT 1", "replacement"),
               ("AGREE 2", "beta"), ("REMOVE 3", "gamma")]
        result = rules.update_rules(initial, ops)
        self.assertEqual(result, [("replacement", 8), ("beta", 5), ("delta", 2)])
        self.assertEqual(result, rules.update_rules(
            initial, ops, expel_edit_count_policy="inherit"))
        self.assertEqual(initial, [("alpha", 7), ("beta", 4), ("gamma", 1)])

    def test_non_edit_operations_identical_with_and_without_cap(self):
        initial = [("alpha", 7), ("beta", 4), ("gamma", 1)]
        ops = [("ADD", "delta"), ("AGREE 2", "beta"), ("REMOVE 1", "alpha"),
               ("REMOVE 3", "gamma")]
        for full, expected in [
            (False, [("alpha", 6), ("beta", 5), ("delta", 2)]),
            (True, [("beta", 5), ("alpha", 4), ("delta", 2)]),
        ]:
            for policy in rules.EDIT_COUNT_POLICIES:
                with self.subTest(full=full, policy=policy):
                    self.assertEqual(rules.update_rules(
                        initial, ops, list_full=full,
                        expel_edit_count_policy=policy), expected)

    def test_duplicate_edit_still_redirects_to_agree(self):
        for policy in rules.EDIT_COUNT_POLICIES:
            events = []
            self.assertEqual(rules.update_rules(
                [("alpha", 7), ("beta", 3)], [("EDIT 1", "beta refined")],
                expel_edit_count_policy=policy, edit_events=events),
                [("alpha", 7), ("beta", 4)])
            self.assertEqual(events, [])

    def test_invalid_edits_do_not_log(self):
        for policy in rules.EDIT_COUNT_POLICIES:
            events = []
            self.assertEqual(rules.update_rules(
                [("old", 7)], [("EDIT 9", "new"), ("EDIT 0", "other")],
                expel_edit_count_policy=policy, edit_events=events), [("old", 7)])
            self.assertEqual(events, [])

    def test_edit_event_values_and_rank_effect(self):
        for policy, expected_count in [("inherit", 8), ("reset", 2)]:
            events = []
            result = rules.update_rules(
                [("old rule", 7), ("other", 5)], [("EDIT 1", "new rule")],
                expel_edit_count_policy=policy, edit_events=events, step=9)
            self.assertEqual(events, [{
                "step": 9, "rule_index": 1, "old_text": "old rule",
                "new_text": "new rule", "old_count": 7,
                "new_count": expected_count, "edit_count_policy": policy,
                "edit_change": 1 - 1/3,
            }])
            self.assertEqual(result[0][0], "new rule" if policy == "inherit" else "other")
            self.assertEqual(rules.render_rules(result),
                             "1. new rule\n2. other" if policy == "inherit"
                             else "1. other\n2. new rule")

    def test_token_jaccard(self):
        for a, b, expected in [
            ("Rule rule!", "RULE", 1.0), ("", "", 1.0),
            ("...", "", 1.0), ("", "new", 0.0),
            ("alpha", "beta", 0.0), ("old rule", "new rule", 1/3),
            ("CAFÉ", "café", 1.0),
        ]:
            with self.subTest(a=a, b=b):
                self.assertAlmostEqual(rules.token_jaccard(a, b), expected)

    def test_policy_validation(self):
        with self.assertRaisesRegex(ValueError, "expel_edit_count_policy"):
            rules.update_rules([], [], expel_edit_count_policy="typo")


class FakeLLM:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.prompts = []

    def generate(self, messages):
        self.prompts.append(messages)
        return next(self.outputs), None


class CompressionTests(unittest.TestCase):
    def setUp(self):
        artifact_root = Path(tempfile.gettempdir()) / "expel-audit-tests"
        artifact_root.mkdir(parents=True, exist_ok=True)
        self.output = Path(tempfile.mkdtemp(dir=artifact_root)) / "mem.txt"
        self.pool = [
            base.PoolEntry(task_id=f"webshop_{i}", taskName="shopping",
                           taskDescription=f"buy item {i}", success=True,
                           trajectory=[{"action": "click[Buy Now]", "observation": "done"}])
            for i in range(3)
        ]
        self.context = {"domain_name": "an online store website",
                        "expel_prompt_variant": "webshop"}

    def compress(self, llm, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            core.ExpeL.compress(self.pool, self.context, llm, self.output,
                                success_chunk_size=1, **kwargs)

    def checkpoint(self):
        return json.loads(self.output.with_suffix(".ckpt.json").read_text())

    def event_log(self):
        return [json.loads(line) for line in
                self.output.with_suffix(".edits.jsonl").read_text().splitlines()]

    def test_policy_reaches_compression_and_durable_log(self):
        for policy, expected_count in [("inherit", 4), ("reset", 2)]:
            # Separate directory per arm, including checkpoint + intermediate files.
            self.output = self.output.parent / policy / "mem.txt"
            llm = FakeLLM(["ADD: old rule.", "AGREE 1: old rule.",
                           "EDIT 1: new rule."])
            self.compress(llm, expel_edit_count_policy=policy, save_intermediate=False)
            checkpoint = self.checkpoint()
            self.assertEqual(checkpoint["rules"], [["new rule.", expected_count]])
            self.assertEqual(checkpoint["expel_edit_count_policy"], policy)
            self.assertEqual(self.event_log(), checkpoint["edit_events"])
            event = self.event_log()[0]
            self.assertEqual((event["step"], event["old_count"], event["new_count"]),
                             (3, 3, expected_count))
            self.assertEqual(self.output.read_text(), "1. new rule.")
            self.assertEqual(len(llm.prompts), 3)
            self.assertNotIn("edit_count_policy", llm.prompts[-1][0]["content"])

    def test_default_and_explicit_inherit_match_prompts_and_memory(self):
        outputs = ["ADD: old rule.", "AGREE 1: old rule.", "EDIT 1: new rule."]
        default_llm = FakeLLM(outputs)
        self.compress(default_llm)
        expected_text = self.output.read_text()
        expected_checkpoint = self.checkpoint()
        expected_snapshots = {
            p.name: p.read_text() for p in
            (self.output.parent / "intermediate_expel").glob("*.txt")
        }
        self.output = self.output.parent / "explicit" / "mem.txt"
        explicit_llm = FakeLLM(outputs)
        self.compress(explicit_llm, expel_edit_count_policy="inherit")
        self.assertEqual(default_llm.prompts, explicit_llm.prompts)
        self.assertEqual(expected_text, self.output.read_text())
        self.assertEqual(expected_checkpoint, self.checkpoint())
        self.assertEqual(expected_snapshots, {
            p.name: p.read_text() for p in
            (self.output.parent / "intermediate_expel").glob("*.txt")
        })

    def test_resume_retains_history_without_duplicate_edits(self):
        llm = FakeLLM(["ADD: old rule.", "EDIT 1: middle rule.", "EDIT 1: new rule."])
        self.compress(llm, expel_edit_count_policy="reset")
        events = self.event_log()
        completed_llm = FakeLLM([])
        self.compress(completed_llm, expel_edit_count_policy="reset")
        self.assertEqual(completed_llm.prompts, [])
        self.assertEqual(self.event_log(), events)
        self.assertEqual(len(events), 2)
        # Simulate a crash after sidecar write, before checkpoint commit.
        checkpoint = self.checkpoint()
        checkpoint.update(step_done=2, rules=[["middle rule.", 2]],
                          edit_events=events[:1])
        self.output.with_suffix(".ckpt.json").write_text(json.dumps(checkpoint))
        resumed_llm = FakeLLM(["EDIT 1: new rule."])
        self.compress(resumed_llm, expel_edit_count_policy="reset")
        self.assertEqual(len(resumed_llm.prompts), 1)
        self.assertEqual(self.event_log(), events)
        self.assertEqual(self.checkpoint()["rules"], [["new rule.", 2]])

    def test_checkpoint_policy_mismatch_rejected_before_llm(self):
        self.compress(FakeLLM(["ADD: old rule.", "", ""]))
        llm = FakeLLM([])
        with self.assertRaisesRegex(ValueError, "checkpoint policy"):
            self.compress(llm, expel_edit_count_policy="reset")
        self.assertEqual(llm.prompts, [])

    def test_legacy_checkpoint_is_inherit(self):
        self.output.with_suffix(".ckpt.json").write_text(json.dumps({
            "step_done": 2, "rules": [["old rule.", 7]],
        }))
        self.compress(FakeLLM(["EDIT 1: new rule."]))
        self.assertEqual(self.checkpoint()["rules"], [["new rule.", 8]])
        self.assertEqual(self.event_log()[0]["old_count"], 7)

    def test_legacy_checkpoint_rejected_for_reset(self):
        self.output.with_suffix(".ckpt.json").write_text(json.dumps({
            "step_done": 2, "rules": [["old rule.", 7]],
        }))
        with self.assertRaisesRegex(ValueError, "checkpoint policy"):
            self.compress(FakeLLM([]), expel_edit_count_policy="reset")

    def test_invalid_policy_rejected_before_artifacts_or_llm(self):
        llm = FakeLLM([])
        with self.assertRaisesRegex(ValueError, "expel_edit_count_policy"):
            self.compress(llm, expel_edit_count_policy="typo")
        self.assertEqual(llm.prompts, [])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix(".ckpt.json").exists())


if __name__ == "__main__":
    unittest.main()
