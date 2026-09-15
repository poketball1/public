#!/usr/bin/env python3
"""test_keepwarm.py — contract tests for the keep-warm reference implementation.

    python3 -m unittest test_keepwarm -v
    python3 test_keepwarm.py            # same thing

Every test below pins a behavior that cost us a real incident. The name says
which one. Fixtures live in `fixtures/` and are plain JSONL — open them; they
are the clearest documentation of what a transcript actually looks like.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

import keepwarm_daemon as kw

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The fixtures anchor at 2026-09-15T10:00:00Z; "now" is that plus an offset.
BASE = datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc)


def at(minutes: float) -> int:
    return int((BASE + timedelta(minutes=minutes)).timestamp() * 1000)


def rows(name: str) -> list[dict]:
    return kw.read_jsonl_tail(FIXTURES / name)


class TestHonestClock(unittest.TestCase):
    """The clock measures 'when did a model last process tokens', full stop."""

    def test_clean_session_clock_tracks_the_assistant_row(self):
        facts = kw.transcript_tail_facts(rows("idle_clean.jsonl"), at(50))
        self.assertEqual(facts.idle_cache_ms, 50 * kw.MINUTE_MS)
        self.assertEqual(facts.effective_idle_ms, 50 * kw.MINUTE_MS)

    def test_failed_injection_does_not_advance_the_clock(self):
        """THE 2026-08-13 INCIDENT, in one assertion.

        A keep-warm turn got an API error. The user row landed at t=52 and a
        `<synthetic>` 0/0 assistant row followed it. The old clock — "time since
        the last row" — read 0 minutes idle, so the cold-cliff guard stayed
        silent and the lane kept firing into a dead cache: 12 overloads in a
        day, 7 measurable turns re-writing 2,623,431 tokens, every one of them
        logged as a success.

        The honest clock reads the real age: 52 minutes.
        """
        facts = kw.transcript_tail_facts(rows("clock_ignores_failed_injection.jsonl"), at(52))
        self.assertEqual(facts.idle_cache_ms, 52 * kw.MINUTE_MS)
        self.assertEqual(facts.idle_row_ms, 0)          # the raw signal DID move
        self.assertEqual(facts.effective_idle_ms, 52 * kw.MINUTE_MS)

    def test_sidechain_rows_do_not_advance_the_clock(self):
        """A sub-agent turn does not refresh the MAIN conversation's cache."""
        facts = kw.transcript_tail_facts(rows("clock_ignores_sidechain.jsonl"), at(55))
        self.assertEqual(facts.idle_cache_ms, 55 * kw.MINUTE_MS)
        self.assertEqual(facts.idle_row_ms, 55 * kw.MINUTE_MS)

    def test_metadata_rows_move_neither_clock_nor_turn_state(self):
        facts = kw.transcript_tail_facts(rows("metadata_only_tail.jsonl"), at(50))
        self.assertEqual(facts.idle_cache_ms, 50 * kw.MINUTE_MS)
        self.assertEqual(facts.turn_state, "ended")

    def test_fallback_order_is_cache_then_row_then_mtime(self):
        facts = kw.TailFacts(idle_cache_ms=None, idle_row_ms=5, idle_mtime_ms=9)
        self.assertEqual(facts.effective_idle_ms, 5)
        facts = kw.TailFacts(idle_cache_ms=None, idle_row_ms=None, idle_mtime_ms=9)
        self.assertEqual(facts.effective_idle_ms, 9)
        # The fallbacks are the OLD behavior, not a safer one. That is why
        # `has_row_evidence` exists: arming refuses an mtime-only clock.
        self.assertFalse(facts.has_row_evidence)

    def test_newborn_has_no_row_evidence(self):
        facts = kw.transcript_tail_facts(rows("newborn.jsonl"), at(50))
        self.assertIsNone(facts.idle_cache_ms)
        self.assertIsNone(facts.idle_row_ms)
        self.assertFalse(facts.has_row_evidence)
        self.assertIsNone(facts.last_assistant_model)


class TestTurnJudge(unittest.TestCase):
    """Never inject into an open turn."""

    def test_finished_turn_is_ended(self):
        self.assertEqual(kw.judge_turn_state(rows("idle_clean.jsonl"), at(50)).state, "ended")

    def test_unanswered_tool_result_is_mid_turn(self):
        turn = kw.judge_turn_state(rows("turn_mid_tool_result.jsonl"), at(50))
        self.assertEqual(turn.state, "mid_turn")
        self.assertIsNone(turn.dialog_tool)

    def test_unanswered_dialog_is_dialog_pending(self):
        turn = kw.judge_turn_state(rows("turn_dialog_pending.jsonl"), at(50))
        self.assertEqual(turn.state, "dialog_pending")
        self.assertEqual(turn.dialog_tool, "AskUserQuestion")

    def test_answered_dialog_is_not_pending(self):
        """The rule is 'is it unanswered', not 'is it visible'.

        Answering writes a user tool_result row, which pushes the last-user
        index past the dialog. An answered dialog still sitting in the tail
        must not hold the lane forever.
        """
        self.assertEqual(kw.judge_turn_state(rows("turn_dialog_answered.jsonl"), at(50)).state,
                         "ended")

    def test_no_content_rows_fails_open_to_ended(self):
        self.assertEqual(kw.judge_turn_state(rows("newborn.jsonl"), at(50)).state, "ended")

    def test_queue_row_is_mid_turn(self):
        self.assertEqual(kw.judge_turn_state(rows("queued.jsonl"), at(50)).state, "mid_turn")


class TestFingerprintAndConfirm(unittest.TestCase):

    def test_nonce_one_does_not_match_nonce_ten(self):
        """`#1` inside `#10` would attribute the wrong row and the wrong verdict."""
        self.assertEqual(kw.inspect_submission(rows("nonce_boundary.jsonl"), "arm_t#1").status,
                         "not_confirmed")
        self.assertEqual(kw.inspect_submission(rows("nonce_boundary.jsonl"), "arm_t#10").status,
                         "confirmed")

    def test_queue_row_confirms_immediately(self):
        """Landing in the CLI's input queue IS a submission success.

        Waiting out the window for a user row after seeing the queue row cost
        every busy-session sender a full window — measured: queued confirms
        landed at exactly 45.0 s, every time, because the window expiring was
        what finally admitted them.
        """
        result = kw.inspect_submission(rows("queued.jsonl"), "arm_t#1")
        self.assertEqual(result.status, "queued_confirmed")

    def test_user_row_wins_over_queue_row_in_the_same_pass(self):
        mixed = rows("queued.jsonl") + rows("verdict_hit.jsonl")
        self.assertEqual(kw.inspect_submission(mixed, "arm_t#1").status, "confirmed")

    def test_retry_message_is_the_original_plus_a_suffix(self):
        now = at(50)
        first = kw.build_message("arm_t", 3, now)
        retry = kw.build_message("arm_t", 3, now, retry=True)
        self.assertEqual(retry, first + " - retry")
        # Same nonce on both copies: if the Enter was swallowed, the original is
        # still in the input box and the retry text appends to it, so one Enter
        # submits the merged line. Either copy confirms.
        self.assertIn("arm_t#3", first)
        self.assertIn("arm_t#3", retry)

    def test_message_stays_inside_the_invariants(self):
        message = kw.build_message("arm_" + "x" * 150, 999, at(0))
        self.assertLessEqual(len(message), kw.MAX_MESSAGE_LEN)
        self.assertNotIn("\n", message)
        self.assertNotIn("\r", message)
        # No idle/elapsed numbers in a model-visible string: wall clock only.
        self.assertNotIn("경과", message)

    def test_relay_normalization_order_is_preserved(self):
        # "a\rb" must become "a b", not "ab".
        self.assertEqual(kw.normalize_for_match("a\rb"), "a b")
        self.assertEqual(kw.normalize_for_match("a\x00b"), "ab")


class TestVerdict(unittest.TestCase):

    def test_cache_hit(self):
        verdict = kw.classify_verdict(rows("verdict_hit.jsonl"), "arm_t#1")
        self.assertEqual(verdict.status, "reached")
        self.assertEqual(verdict.cache_outcome, "hit")

    def test_cache_rewrite_is_still_reached(self):
        """`read > 0` alone cannot mean 'hit'.

        The shared workspace system+tools prefix (~20-30k tokens) stays warm via
        concurrent sessions, so a turn that re-paid the ENTIRE conversation body
        still reads a positive number. Measured body-survival ratios are bimodal
        (~1.0 and ~0.0), which is why `read >= creation` is the split.

        A rewrite still refills the cache, so it is still `reached` and still
        spends a count. What was wrong before was not the verdict — it was the
        silence about the cost.
        """
        verdict = kw.classify_verdict(rows("verdict_rewrite.jsonl"), "arm_t#1")
        self.assertEqual(verdict.status, "reached")
        self.assertEqual(verdict.cache_outcome, "rewrite")
        self.assertEqual(verdict.cache_creation, 553655)

    def test_zero_usage_is_not_reached_even_across_an_attachment_row(self):
        """The harness interposes rows between a user row and its assistant.

        A strict `parentUuid == injected.uuid` rule scored 135 no-verdicts out
        of 135 the day `attachment` rows appeared — the budget stopped being
        spent and limit-suspend went blind, silently. Attribution walks the
        chain across non-turn rows; a user/assistant ancestor still stops it,
        which is what keeps another turn's answer from being stolen.
        """
        verdict = kw.classify_verdict(rows("verdict_not_reached_via_attachment.jsonl"), "arm_t#1")
        self.assertEqual(verdict.status, "not-reached")
        self.assertEqual(verdict.reason, "cache_usage_zero")
        self.assertIsNone(verdict.cache_outcome)
        self.assertTrue(verdict.is_api_error)
        self.assertEqual(verdict.api_error_status, 429)

    def test_attribution_stops_at_a_turn_boundary(self):
        """An assistant belonging to a different turn must never be attributed."""
        forged = rows("verdict_hit.jsonl") + [{
            "type": "user", "uuid": "other-user", "parentUuid": "a1",
            "timestamp": "2026-09-15T11:00:00Z",
            "message": {"role": "user", "content": "무관한 질문"},
        }, {
            "type": "assistant", "uuid": "other-asst", "parentUuid": "other-user",
            "timestamp": "2026-09-15T11:00:00Z",
            "message": {"role": "assistant", "model": "claude-opus-5",
                        "content": [{"type": "text", "text": "답"}],
                        "usage": {"cache_read_input_tokens": 9,
                                  "cache_creation_input_tokens": 9}},
        }]
        verdict = kw.classify_verdict(forged, "arm_t#1")
        self.assertEqual(verdict.assistant_uuid, "a1")   # ours, not the later one

    def test_missing_assistant_is_pending_not_failure(self):
        only_user = [r for r in rows("verdict_hit.jsonl") if r.get("type") != "assistant"]
        self.assertEqual(kw.classify_verdict(only_user, "arm_t#1").status, "pending")


class TestResume(unittest.TestCase):

    def test_positive_cache_after_the_watermark_is_ready(self):
        verdict = kw.classify_resume(rows("resume_ready.jsonl"), "a1")
        self.assertEqual(verdict["status"], "ready")
        self.assertEqual(verdict["assistant_uuid"], "a2")

    def test_transcript_movement_alone_is_not_resume(self):
        """THE TRAP. The limit response itself moves the transcript.

        A rule like "it is advancing again, so the limit must be over" resumes
        straight into a dead cache. Only positive cache usage counts.
        """
        verdict = kw.classify_resume(rows("resume_waiting.jsonl"), "a1")
        self.assertEqual(verdict["status"], "waiting")
        self.assertEqual(verdict["reason"], "positive_cache_usage_not_found")

    def test_missing_watermark_waits_rather_than_guesses(self):
        self.assertEqual(kw.classify_resume(rows("resume_ready.jsonl"), None)["status"], "waiting")


class TestModelPolicy(unittest.TestCase):

    def test_pattern_table(self):
        self.assertEqual(kw.model_budget("claude-fable-5"), "unbounded")
        self.assertEqual(kw.model_budget("claude-opus-5"), "bounded")
        self.assertEqual(kw.model_budget("claude-opus-5[1m]"), "bounded")
        self.assertEqual(kw.model_budget("claude-sonnet-5"), "ineligible")
        self.assertEqual(kw.model_budget("claude-haiku-4-5-20251001"), "ineligible")

    def test_unknown_behaves_as_bounded_because_absence_is_not_a_verdict(self):
        for value in (None, "", "   ", "<synthetic>", 5, {}):
            self.assertEqual(kw.model_budget(value), "unknown")

    def test_first_match_wins(self):
        self.assertEqual(kw.model_budget("claude-fable-opus-hybrid"), "unbounded")

    def test_policy_reads_off_the_fixtures(self):
        facts = kw.transcript_tail_facts(rows("model_ineligible.jsonl"), at(1))
        self.assertEqual(kw.model_budget(facts.last_assistant_model), "ineligible")
        facts = kw.transcript_tail_facts(rows("model_unbounded.jsonl"), at(1))
        self.assertEqual(kw.model_budget(facts.last_assistant_model), "unbounded")


class TestBudgetAndAutomaticPlan(unittest.TestCase):

    def test_absent_state_gets_the_unattended_default(self):
        plan = kw.automatic_arm_plan(None)
        self.assertEqual(plan, {"action": "arm", "count": kw.DEFAULT_UNATTENDED_COUNT,
                                "prior": None, "recovery_reason": "state_missing"})

    def test_terminal_debris_hands_over_the_exact_remainder(self):
        """An automatic actor never CREATES budget.

        Two terminal paths used to delete the state file, and the spent count
        lived only there — so the next automatic arm read 'absent' and granted a
        fresh 24. One measured session spent 1, died, and got 24 back.
        """
        plan = kw.automatic_arm_plan(
            {"status": "cold_missed", "count_budget": 24, "confirmed_count": 7})
        self.assertEqual(plan["action"], "arm")
        self.assertEqual(plan["count"], 17)
        self.assertEqual(plan["recovery_reason"], "terminal_debris:cold_missed")

    def test_opt_out_beats_everything(self):
        for budget in ("unbounded", "bounded", "ineligible", None):
            plan = kw.automatic_arm_plan({"status": "stopped", "count_budget": 24,
                                          "confirmed_count": 0}, budget=budget)
            self.assertEqual(plan["reason"], "opted_out")

    def test_exhausted_is_skipped_for_a_bounded_model(self):
        plan = kw.automatic_arm_plan({"status": "count_exhausted",
                                      "count_budget": 24, "confirmed_count": 24},
                                     budget="bounded")
        self.assertEqual(plan, {"action": "skip", "reason": "count_exhausted",
                                "prior": plan["prior"]})

    def test_exhausted_is_revived_for_an_unbounded_model(self):
        """An unbounded model has no count to consume.

        An exhausted-looking snapshot on such a session is a leftover from the
        arm that ran BEFORE the model was known. Reviving it is what "stays warm
        until you say off" means.
        """
        plan = kw.automatic_arm_plan({"status": "count_exhausted",
                                      "count_budget": 24, "confirmed_count": 24},
                                     budget="unbounded")
        self.assertEqual(plan["action"], "arm")
        self.assertEqual(plan["recovery_reason"], "unbounded_model_revive")

    def test_exhausted_on_an_ineligible_model_says_so(self):
        """The honest reason. "Exhausted" is true about the counter and
        misleading about the sid — the spent budget is not why it will never be
        armed again."""
        plan = kw.automatic_arm_plan({"status": "count_exhausted",
                                      "count_budget": 24, "confirmed_count": 24},
                                     budget="ineligible")
        self.assertEqual(plan["reason"], "model_ineligible")

    def test_malformed_counters_fail_closed(self):
        for prior in ({"status": "cold_missed", "count_budget": "twelve", "confirmed_count": 0},
                      {"status": "cold_missed", "count_budget": -1, "confirmed_count": 0},
                      {"status": "cold_missed", "count_budget": 24},
                      {"status": "cold_missed", "count_budget": 24, "confirmed_count": 1.5}):
            self.assertEqual(kw.automatic_arm_plan(prior)["action"], "skip")

    def test_a_live_incumbent_is_never_churned(self):
        plan = kw.automatic_arm_plan({"status": "armed", "count_budget": 24,
                                      "confirmed_count": 1}, nonterminal_liveness="alive")
        self.assertEqual(plan["reason"], "existing_arm:armed")

    def test_indeterminate_identity_blocks_takeover(self):
        """A probe error is not evidence of death."""
        plan = kw.automatic_arm_plan({"status": "armed", "count_budget": 24,
                                      "confirmed_count": 1},
                                     nonterminal_liveness="indeterminate")
        self.assertEqual(plan["reason"], "daemon_identity_indeterminate")

    def test_debris_retention_rule(self):
        self.assertTrue(kw.keeps_debris("stopped", 0))
        self.assertTrue(kw.keeps_debris("count_exhausted", 0))
        self.assertTrue(kw.keeps_debris("cold_missed", 0))
        # Emission history alone keeps nothing — that story belongs to the
        # ledger. A SPENT budget does, because the state file is its only
        # carrier.
        self.assertFalse(kw.keeps_debris("session_dead", 0))
        self.assertTrue(kw.keeps_debris("session_dead", 1))


class TestTimingWindow(unittest.TestCase):

    def test_fire_window_must_be_at_least_one_tick_wide(self):
        """Otherwise a daemon steps from 'not idle yet' straight past the cliff
        and never fires, silently. An env override can do exactly that."""
        with self.assertRaises(ValueError):
            kw.assert_timing_window(fire_at_ms=50 * kw.MINUTE_MS,
                                    cold_at_ms=51 * kw.MINUTE_MS,
                                    tick_ms=240_000)
        kw.assert_timing_window(fire_at_ms=50 * kw.MINUTE_MS,
                                cold_at_ms=57 * kw.MINUTE_MS,
                                tick_ms=240_000)

    def test_delivery_ladder_fits_inside_the_cache_slack(self):
        """55.8 min TTL edge - 52 min (latest-firing lane) - 1 min jitter."""
        slack_ms = 3_348_000 - 3_120_000 - 60_000
        self.assertEqual(slack_ms, 168_000)
        ladder = kw.CONFIRM_MS + kw.RETRY_CONFIRM_MS * 2
        self.assertLessEqual(ladder, slack_ms)


class TestTickOutcomes(unittest.TestCase):
    """End-to-end tick decisions, with the transport stubbed out."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sessions = self.root / "sessions"
        self.sessions.mkdir()
        # A live registry row: our own PID, so liveness reads `alive`.
        import os
        (self.sessions / f"{os.getpid()}.json").write_text(json.dumps({
            "sessionId": "test-sid", "cwd": "/tmp/x",
            "kind": "interactive", "entrypoint": "cli",
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def make_arm(self, fixture: str, **kwargs) -> kw.Arm:
        transcript = self.root / "t.jsonl"
        transcript.write_bytes((FIXTURES / fixture).read_bytes())
        defaults = dict(
            sid="test-sid", arm_id="arm_t", transcript=transcript,
            state_dir=self.root / "state", ledger=self.root / "keepwarm.jsonl",
            transport=kw.DryRunTransport(), sessions_dir=self.sessions,
        )
        defaults.update(kwargs)
        return kw.Arm(**defaults)

    def test_not_idle_yet(self):
        arm = self.make_arm("idle_clean.jsonl")
        self.assertEqual(kw.tick(arm, at(10)), "not_idle")

    def test_cold_cliff_terminates_rather_than_firing(self):
        """The hard rule: never reheat a cold session.

        A fire here pays a full rewrite for a turn nobody asked for — the exact
        accident this infrastructure exists to prevent.
        """
        arm = self.make_arm("idle_clean.jsonl")
        self.assertEqual(kw.tick(arm, at(58)), "past_ttl_cliff")
        self.assertEqual(arm.seq, 0)          # nothing was ever sent

    def test_open_dialog_holds_the_fire(self):
        arm = self.make_arm("turn_dialog_pending.jsonl")
        self.assertEqual(kw.tick(arm, at(52)), "turn_hold")
        self.assertEqual(arm.seq, 0)

    def test_mid_turn_holds_the_fire(self):
        arm = self.make_arm("turn_mid_tool_result.jsonl")
        self.assertEqual(kw.tick(arm, at(52)), "turn_hold")

    def test_ineligible_model_ends_the_arm(self):
        arm = self.make_arm("model_ineligible.jsonl")
        self.assertEqual(kw.tick(arm, at(52)), "model_ineligible")

    def test_natal_waits_without_firing_and_without_spending(self):
        """A newborn has no model and no row-anchored clock, so the effective
        clock would fall through to mtime. Firing on mtime is the cold-reheat
        accident. Natal does not enter the firing machine at all — a structural
        guarantee, not a threshold. And waiting costs nothing."""
        arm = self.make_arm("newborn.jsonl", natal=True)
        self.assertEqual(kw.tick(arm, at(99)), "natal_wait")
        self.assertEqual(arm.confirmed_count, 0)
        self.assertTrue(arm.natal)

    def test_natal_resolves_once_both_kinds_of_evidence_exist(self):
        arm = self.make_arm("idle_clean.jsonl", natal=True)
        self.assertEqual(kw.tick(arm, at(10)), "natal_resolved")
        self.assertFalse(arm.natal)
        self.assertEqual(arm.model, "claude-opus-5")
        self.assertEqual(arm.confirmed_count, 0)   # natal spends nothing

    def test_natal_past_the_warm_margin_keeps_waiting(self):
        """It must not escape into the standard loop only to die `cold_missed`
        on its first tick — we watched arms do exactly that."""
        arm = self.make_arm("idle_clean.jsonl", natal=True)
        self.assertEqual(kw.tick(arm, at(58)), "natal_wait")
        self.assertTrue(arm.natal)

    def test_dead_session_reports_not_live(self):
        arm = self.make_arm("idle_clean.jsonl", sid="ghost-sid")
        self.assertEqual(kw.tick(arm, at(52)), "not_live")

    def test_fire_confirm_verdict_and_budget(self):
        """The full happy path, using the echoing dry-run transport."""
        transcript = self.root / "t.jsonl"
        transcript.write_bytes((FIXTURES / "idle_clean.jsonl").read_bytes())
        arm = self.make_arm(
            "idle_clean.jsonl",
            transport=kw.DryRunTransport(echo_transcript=transcript),
            count_budget=2,
        )
        outcome = kw.tick(arm, at(52))
        self.assertEqual(outcome, "emitted")
        self.assertEqual(arm.emit_count, 1)
        self.assertEqual(arm.confirmed_count, 1)     # a reached verdict spent one
        self.assertEqual(arm.seq, 1)

    def test_budget_exhaustion_on_a_bounded_model(self):
        transcript = self.root / "t.jsonl"
        transcript.write_bytes((FIXTURES / "idle_clean.jsonl").read_bytes())
        arm = self.make_arm(
            "idle_clean.jsonl",
            transport=kw.DryRunTransport(echo_transcript=transcript),
            count_budget=1,
        )
        self.assertEqual(kw.tick(arm, at(52)), "count_exhausted")
        self.assertEqual(arm.confirmed_count, 1)

    def test_unbounded_model_never_exhausts(self):
        transcript = self.root / "t.jsonl"
        transcript.write_bytes((FIXTURES / "model_unbounded.jsonl").read_bytes())
        arm = self.make_arm(
            "model_unbounded.jsonl",
            transport=kw.DryRunTransport(echo_transcript=transcript,
                                         echo_model="claude-fable-5"),
            count_budget=1,
        )
        self.assertEqual(kw.tick(arm, at(52)), "emitted")
        self.assertEqual(arm.confirmed_count, 1)
        self.assertTrue(arm.budget_unbounded)

    def test_limit_answer_suspends_without_spending_or_terminating(self):
        """A 0/0 answer is a temporary model state, not a delivery failure and
        not a death. Suspend preserves the budget, the daemon, and the watermark
        we need in order to know when it is safe to resume."""
        transcript = self.root / "t.jsonl"
        transcript.write_bytes((FIXTURES / "idle_clean.jsonl").read_bytes())
        arm = self.make_arm(
            "idle_clean.jsonl",
            transport=kw.DryRunTransport(echo_transcript=transcript,
                                         echo_usage=(0, 0)),
            count_budget=3,
        )
        self.assertEqual(kw.tick(arm, at(52)), "suspended")
        self.assertTrue(arm.suspended)
        self.assertEqual(arm.confirmed_count, 0)          # budget preserved
        self.assertIsNotNone(arm.watermark_assistant_uuid)
        self.assertEqual(arm.suspension_reason, "suspended_limit")

    def test_delivery_failure_terminates_the_arm(self):
        """A failed warm turn costs no tokens — but the cache is dead anyway,
        and an arm has no guaranteed future consumer, so every later turn would
        pay cold in full. Terminating is the honest answer."""
        class BrokenTransport(kw.Transport):
            name = "broken"

            def deliver(self, sid, message):
                return None      # pretends to succeed, never lands

        arm = self.make_arm("idle_clean.jsonl", transport=BrokenTransport())
        # Make the confirm windows instant so the test does not sleep.
        original = kw.wait_for_submission
        kw.wait_for_submission = lambda *a, **k: kw.ConfirmResult("not_confirmed")
        try:
            self.assertEqual(kw.tick(arm, at(52)), "delivery_failed")
        finally:
            kw.wait_for_submission = original


class TestLedgerAndState(unittest.TestCase):

    def test_state_file_carries_the_derived_budget_boolean(self):
        """The statusline must never re-implement the model policy."""
        arm = kw.Arm(sid="s", arm_id="a", transcript=Path("/x"),
                     state_dir=Path("/x"), ledger=Path("/x"),
                     transport=kw.DryRunTransport(), sessions_dir=Path("/x"),
                     model="claude-fable-5")
        self.assertTrue(arm.snapshot()["budget_unbounded"])
        arm.model = "claude-opus-5"
        self.assertFalse(arm.snapshot()["budget_unbounded"])

    def test_ledger_row_is_one_json_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "l.jsonl"
            kw.append_ledger(ledger, {"event": "armed", "sid": "s"})
            kw.append_ledger(ledger, {"event": "terminated", "sid": "s"})
            lines = ledger.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["event"], "terminated")

    def test_atomic_write_never_leaves_a_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "s.json"
            kw.atomic_write_json(target, {"a": 1})
            kw.atomic_write_json(target, {"a": 2})
            self.assertEqual(json.loads(target.read_text())["a"], 2)
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])


class TestBoundedReads(unittest.TestCase):

    def test_tail_read_is_bounded_and_drops_the_torn_first_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.jsonl"
            with path.open("w", encoding="utf-8") as fh:
                for i in range(5000):
                    fh.write(json.dumps({"type": "user", "uuid": f"u{i}",
                                         "timestamp": "2026-09-15T10:00:00Z",
                                         "message": {"role": "user",
                                                     "content": "x" * 200}}) + "\n")
            parsed = kw.read_jsonl_tail(path, max_bytes=8 * 1024)
            self.assertLess(len(parsed), 5000)
            self.assertTrue(all(isinstance(r, dict) for r in parsed))
            # Transcripts reach tens of MB. A full slurp is an OOM class of bug,
            # so every reader in the lane is bounded the same way.


if __name__ == "__main__":
    unittest.main(verbosity=2)
