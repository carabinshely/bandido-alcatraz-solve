"""Narrow synthetic admission tests; never allocates seeds or runs games."""
import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).resolve().parents[1] / "experiments/paired34/issuance.py"
SPEC = importlib.util.spec_from_file_location("paired34_issuance", PATH)
ISSUANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ISSUANCE)
HEAD = "a" * 40
NONCE = "b" * 64


def review(reviewer):
    return dict(reviewer=reviewer, head=HEAD,
                verdict="NO_ACTIONABLE_P0_P3", report_sha256="c" * 64)


class Client:
    def __init__(self, details):
        self.calls = []
        self.details = details

    def request(self, method, path, data, label):
        self.calls.append(label)
        if label == "first_issue_comments":
            return 200, [dict(id=5, user=dict(login="carabinshely"),
                              issue_url=ISSUANCE.BASE + "/issues/66",
                              body="PAIRED34_FIRST_ISSUE_V1\n" +
                              ISSUANCE.canonical(self.details).decode(),
                              created_at="2026-10-21T05:00:00Z",
                              updated_at="2026-10-21T05:00:00Z")]
        if label == "first_issue_runs":
            return 200, dict(total_count=1, workflow_runs=[dict(
                id=123, head_sha=HEAD, event="pull_request", run_attempt=1,
                path=".github/workflows/paired34.yml", pull_requests=[dict(number=66)],
                status="in_progress", conclusion=None,
                created_at="2026-10-21T05:01:00Z")])
        raise AssertionError(label)


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.exhaustive = review("sol61-medium")
        self.adversarial = review("ponytail-adversarial")
        self.root_go = "ROOT_GO_EXACT_HEAD_REVIEWS_VERIFIED"
        self.details = dict(allocation=ISSUANCE.ALLOCATION, head=HEAD, nonce=NONCE,
                            root_intent="intent-sha", pr_number=66,
                            exhaustive_review=self.exhaustive,
                            adversarial_review=self.adversarial, root_go=self.root_go)

    def validate(self, client, **changes):
        args = dict(head=HEAD, run_id="123", pr_number=66,
                    root_intent="intent-sha", comment_id=5, nonce=NONCE,
                    global_created_at="2026-10-21T04:59:00Z",
                    exhaustive_review=self.exhaustive,
                    adversarial_review=self.adversarial, root_go=self.root_go)
        args.update(changes)
        return ISSUANCE.validate_first_run(client, **args)

    def test_exact_authenticated_root_attestation(self):
        self.assertEqual(self.validate(Client(self.details))["run_id"], "123")

    def test_pr_body_placeholders_cannot_reach_claim(self):
        client = Client(self.details)
        with self.assertRaisesRegex(ValueError, "FIRST_ISSUE_REVIEW_RECEIPT"):
            self.validate(client, exhaustive_review="looks reviewed")
        self.assertEqual(client.calls, [])

    def test_changed_report_hash_fails_authenticated_comment_join(self):
        client = Client(self.details)
        changed = dict(self.exhaustive, report_sha256="d" * 64)
        with self.assertRaisesRegex(ValueError, "FIRST_ISSUE_COMMENT_BODY"):
            self.validate(client, exhaustive_review=changed)
        self.assertEqual(client.calls, ["first_issue_comments"])

    def test_missing_root_go_fails_before_remote_read(self):
        client = Client(self.details)
        with self.assertRaisesRegex(ValueError, "FIRST_ISSUE_ROOT_GO"):
            self.validate(client, root_go="pending")
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
