"""One fixed allocation claim through GitHub's atomic Create-reference API.
Docs: https://docs.github.com/en/rest/git/refs#create-a-reference
      https://docs.github.com/en/rest/git/tags#create-a-tag-object
No project imports; network is permitted only inside the root-admitted CI driver.
"""
import json
import http.client
import os
import re
from datetime import datetime, timezone
import urllib.error
import urllib.request

REPO = "carabinshely/bandido-alcatraz-solve"
BASE = "https://api.github.com/repos/" + REPO
ALLOCATION = "bandido-seeds-1000491-1000502"
REF = "refs/tags/" + ALLOCATION
GLOBAL_BRANCH = "codex/seed-allocation-1000491-1000502"
GLOBAL_REF = "refs/heads/" + GLOBAL_BRANCH
MAX_RESPONSE = 65536

def require(ok, message):
    if not ok:
        raise ValueError(message)

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode() + b"\n"

def write_new(path, raw):
    with path.open("xb") as f:
        require(f.write(raw) == len(raw), "ISSUANCE_SHORT_WRITE_UNKNOWN")
        f.flush()
        os.fsync(f.fileno())

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class Client:
    def __init__(self, token, control):
        require(type(token) is str and 0 < len(token) <= 8192, "ISSUANCE_TOKEN_ABSENT")
        self.token = token
        self.control = control
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, data, label):
        fixed = (method, path, label) in (
            ("GET", "/git/ref/tags/" + ALLOCATION, "check"),
            ("POST", "/git/tags", "tag"),
            ("POST", "/git/refs", "ref"),
            ("GET", "/git/ref/tags/" + ALLOCATION, "readback"))
        first_issue_comments = (method == "GET" and label == "first_issue_comments"
                                and re.fullmatch(r"/issues/[1-9][0-9]{0,9}/comments\?per_page=100", path))
        first_issue_runs = (method == "GET" and label == "first_issue_runs"
                            and re.fullmatch(r"/actions/workflows/paired29.yml/runs\?event=pull_request&head_sha=[0-9a-f]{40}&per_page=8", path))
        global_ref = (method == "GET" and label == "global_preissue_ref" and
                      path == "/git/ref/heads/" + GLOBAL_BRANCH)
        global_commit = (method == "GET" and label == "global_preissue_commit" and
                         re.fullmatch(r"/git/commits/[0-9a-f]{40}", path))
        head_commit = (method == "GET" and label == "global_head_commit" and
                       re.fullmatch(r"/git/commits/[0-9a-f]{40}", path))
        require(fixed or first_issue_comments or first_issue_runs or global_ref or global_commit or head_commit,
                "ISSUANCE_ENDPOINT")
        payload = None if data is None else canonical(data)
        require(payload is None or len(payload) <= 8192, "ISSUANCE_REQUEST_CAP")
        # Intent is durable before each distinct HTTP operation; never logs auth.
        write_new(self.control / ("issuance-" + label + "-request.json"),
                  canonical(dict(method=method, path=path, body=data)))
        req = urllib.request.Request(BASE + path, data=payload, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Accept-Encoding": "identity",
            "Accept": "application/vnd.github+json", "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "Bandido-fixed-issuance13"})
        try:
            response = self.opener.open(req, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            status = response.code
            lengths = response.headers.get_all("Content-Length", [])
            transfers = response.headers.get_all("Transfer-Encoding", [])
            encodings = response.headers.get_all("Content-Encoding", [])
            declared = None
            if len(lengths) == 1 and re.fullmatch(r"[0-9]{1,10}", lengths[0]):
                declared = int(lengths[0])
            # Support only unambiguous length or stdlib-validated chunk framing.
            framing = ((declared is not None and not transfers)
                       or (not lengths and transfers == ["chunked"]))
            framing = framing and (not encodings or encodings == ["identity"])
            raw = b""
            eof = False
            try:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) <= MAX_RESPONSE:
                    eof = response.read(1) == b""
            except http.client.IncompleteRead as exc:
                raw += exc.partial
                framing = False
            complete = (framing and eof and len(raw) <= MAX_RESPONSE
                        and (declared is None or len(raw) == declared))
        write_new(self.control / ("issuance-" + label + "-response.bin"), raw[:MAX_RESPONSE])
        write_new(self.control / ("issuance-" + label + "-response-meta.json"),
                  canonical(dict(status=status, observed_bytes=len(raw),
                                 declared_bytes=declared, complete=complete)))
        require(len(raw) <= MAX_RESPONSE, "ISSUANCE_RESPONSE_OVERSIZE_UNKNOWN")
        require(complete, "ISSUANCE_RESPONSE_FRAMING_UNKNOWN")
        return status, json.loads(raw)


def utc_second(value):
    require(type(value) is str and re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value),
            "FIRST_ISSUE_TIME_FORMAT")
    return datetime.fromisoformat(value[:-1]).replace(tzinfo=timezone.utc)


def global_message(head, pr_number, root_intent, nonce):
    return canonical(dict(schema="bandido-first-issue-v1", allocation=ALLOCATION,
                          head=head, pr_number=pr_number, root_intent=root_intent,
                          nonce=nonce, seeds=list(range(1000491, 1000503)))).decode()[:-1]


def validate_global_preissue(client, *, head, pr_number, root_intent, nonce,
                             allocation_commit_sha):
    """The fixed global branch is created by root before the FIRST marker edit."""
    require(type(head) is str and re.fullmatch(r"[0-9a-f]{40}", head), "GLOBAL_HEAD")
    require(type(pr_number) is int and 1 <= pr_number <= 9999999999, "GLOBAL_PR")
    require(type(root_intent) is str and 0 < len(root_intent) <= 256, "GLOBAL_ROOT")
    require(type(nonce) is str and re.fullmatch(r"[0-9a-f]{64}", nonce), "GLOBAL_NONCE")
    require(type(allocation_commit_sha) is str and
            re.fullmatch(r"[0-9a-f]{40}", allocation_commit_sha), "GLOBAL_COMMIT_SHA")
    status, ref = client.request("GET", "/git/ref/heads/" + GLOBAL_BRANCH,
                                 None, "global_preissue_ref")
    require(status == 200 and type(ref) is dict and ref.get("ref") == GLOBAL_REF and
            ref.get("object", {}).get("type") == "commit" and
            ref["object"].get("sha") == allocation_commit_sha,
            "GLOBAL_FIRST_ISSUE_REF")
    status, commit = client.request("GET", "/git/commits/" + allocation_commit_sha,
                                    None, "global_preissue_commit")
    require(status == 200 and type(commit) is dict and
            commit.get("sha") == allocation_commit_sha and
            type(commit.get("parents")) is list and len(commit["parents"]) == 1 and
            commit["parents"][0].get("sha") == head and
            commit.get("message") == global_message(head, pr_number, root_intent, nonce),
            "GLOBAL_FIRST_ISSUE_COMMIT")
    status, reviewed = client.request("GET", "/git/commits/" + head,
                                      None, "global_head_commit")
    require(status == 200 and type(reviewed) is dict and reviewed.get("sha") == head and
            type(reviewed.get("tree")) is dict and
            type(reviewed["tree"].get("sha")) is str and
            re.fullmatch(r"[0-9a-f]{40}", reviewed["tree"]["sha"]) and
            type(commit.get("tree")) is dict and
            commit["tree"].get("sha") == reviewed["tree"]["sha"],
            "GLOBAL_FIRST_ISSUE_TREE")
    created_at = commit.get("committer", {}).get("date")
    utc_second(created_at)
    return dict(branch=GLOBAL_BRANCH, ref=GLOBAL_REF, commit_sha=allocation_commit_sha,
                commit_created_at=created_at, head=head, pr_number=pr_number,
                allocation=ALLOCATION)


def validate_first_run(client, *, head, run_id, pr_number, root_intent, comment_id, nonce,
                       global_created_at):
    """Provider-persisted first event must be this run, before any allocation mutation.

    Root posts the unique first-issue comment BEFORE adding a GO marker. GitHub
    records an Actions run even when its first step fails. A later body edit sees
    the older run and cannot treat an absent allocation ref as an unused cohort.
    Missing/incomplete history or an expired first event fails closed.
    """
    require(type(head) is str and re.fullmatch(r"[0-9a-f]{40}", head), "FIRST_ISSUE_HEAD")
    require(type(run_id) is str and re.fullmatch(r"[1-9][0-9]{0,19}", run_id), "FIRST_ISSUE_RUN")
    require(type(pr_number) is int and 1 <= pr_number <= 9999999999, "FIRST_ISSUE_PR")
    require(type(comment_id) is int and 1 <= comment_id <= 9999999999999999999, "FIRST_ISSUE_COMMENT_ID")
    require(type(nonce) is str and re.fullmatch(r"[0-9a-f]{64}", nonce), "FIRST_ISSUE_NONCE")
    require(type(root_intent) is str and 0 < len(root_intent) <= 256, "FIRST_ISSUE_ROOT")
    status, comments = client.request("GET", f"/issues/{pr_number}/comments?per_page=100",
                                      None, "first_issue_comments")
    require(status == 200 and type(comments) is list and len(comments) < 100,
            "FIRST_ISSUE_COMMENTS_INCOMPLETE")
    require(all(type(c) is dict and type(c.get("body")) is str for c in comments),
            "FIRST_ISSUE_COMMENT_ROW_UNKNOWN")
    candidates = [c for c in comments if type(c) is dict and
                  type(c.get("body")) is str and
                  c["body"].startswith("PAIRED29_FIRST_ISSUE_V1\n")]
    require(len(candidates) == 1, "FIRST_ISSUE_COMMENT_NOT_UNIQUE")
    c = candidates[0]
    require(c.get("id") == comment_id and
            c.get("user", {}).get("login") == "carabinshely" and
            c.get("issue_url") == f"{BASE}/issues/{pr_number}",
            "FIRST_ISSUE_COMMENT_BINDING")
    body = c["body"].split("\n", 1)[1]
    try:
        details = json.loads(body)
    except (ValueError, TypeError):
        raise ValueError("FIRST_ISSUE_COMMENT_JSON") from None
    require(type(details) is dict and set(details) ==
            {"allocation", "head", "nonce", "root_intent", "pr_number"} and
            details == dict(allocation=ALLOCATION, head=head, nonce=nonce,
                            root_intent=root_intent, pr_number=pr_number),
            "FIRST_ISSUE_COMMENT_BODY")
    # Committer time is author supplied. It records the root claim but cannot
    # exclude a prior provider-created workflow run.
    utc_second(global_created_at)
    comment_at = utc_second(c.get("created_at"))
    comment_updated_at = utc_second(c.get("updated_at"))
    require(comment_updated_at >= comment_at, "FIRST_ISSUE_COMMENT_TIME_ORDER")
    path = f"/actions/workflows/paired29.yml/runs?event=pull_request&head_sha={head}&per_page=8"
    status, listing = client.request("GET", path, None, "first_issue_runs")
    require(status == 200 and type(listing) is dict and
            type(listing.get("total_count")) is int and
            1 <= listing["total_count"] <= 8 and
            type(listing.get("workflow_runs")) is list and
            len(listing["workflow_runs"]) == listing["total_count"],
            "FIRST_ISSUE_RUNS_INCOMPLETE")
    eligible = []
    seen = set()
    for run in listing["workflow_runs"]:
        require(type(run) is dict and type(run.get("id")) is int and
                run["id"] > 0 and run["id"] not in seen and
                run.get("head_sha") == head and run.get("event") == "pull_request" and
                type(run.get("run_attempt")) is int and run["run_attempt"] >= 1,
                "FIRST_ISSUE_RUN_ROW")
        raw_path = run.get("path")
        require(type(raw_path) is str, "FIRST_ISSUE_RUN_PATH_UNKNOWN")
        base_path, separator, ref = raw_path.partition("@")
        require(base_path == ".github/workflows/paired29.yml" and
                (not separator or
                 (re.fullmatch(r"[A-Za-z0-9_./-]{1,200}", ref) is not None and
                  ".." not in ref and "//" not in ref and not ref.startswith("/"))),
                "FIRST_ISSUE_RUN_PATH_UNKNOWN")
        seen.add(run["id"])
        require(
                type(run.get("pull_requests")) is list and
                any(type(p) is dict and p.get("number") == pr_number
                    for p in run["pull_requests"]), "FIRST_ISSUE_RUN_ROW")
        when = utc_second(run.get("created_at"))
        # Open/synchronize events before GO have skipped jobs. Every other
        # exact-head attempt spends this first issue, even when it failed.
        if (run.get("status") == "completed" and run.get("conclusion") == "skipped"
                and run["run_attempt"] == 1):
            continue
        eligible.append((when, run["id"]))
    require(eligible, "FIRST_ISSUE_NO_RUN")
    eligible.sort()
    require(len(eligible) == 1 or eligible[0][0] != eligible[1][0],
            "FIRST_ISSUE_RUN_TIME_TIE")
    first_when, first_id = eligible[0]
    require(comment_updated_at < first_when, "FIRST_ISSUE_COMMENT_AFTER_RUN")
    require((first_when - comment_updated_at).total_seconds() <= 300,
            "FIRST_ISSUE_EVENT_EXPIRED")
    require(str(first_id) == run_id, "FIRST_RUN_ALREADY_SPENT")
    return dict(comment_id=comment_id, comment_created_at=c["created_at"],
                global_created_at=global_created_at,
                run_id=run_id, first_run_created_at=first_when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                allocation=ALLOCATION, head=head, pr_number=pr_number)

def claim(client, head, run_id, attempt, root_intent):
    require(type(head) is str and re.fullmatch("[0-9a-f]{40}", head), "ISSUANCE_HEAD")
    require(type(run_id) is str and re.fullmatch("[1-9][0-9]{0,19}", run_id), "ISSUANCE_RUN")
    require(attempt == "1", "ISSUANCE_ATTEMPT")
    require(type(root_intent) is str and 0 < len(root_intent) <= 256, "ISSUANCE_ROOT")
    status, old = client.request("GET", "/git/ref/tags/" + ALLOCATION, None, "check")
    require(status == 404, "ALLOCATION_ALREADY_ISSUED_OR_CHECK_NOT_404")
    message = canonical(dict(schema="bandido-fixed-allocation-issuance-v1",
        allocation=ALLOCATION, seeds=list(range(1000491, 1000503)), head=head,
        run_id=run_id, run_attempt=attempt, root_intent=root_intent)).decode()
    tag_request = dict(tag=ALLOCATION, message=message, object=head, type="commit")
    status, tag = client.request("POST", "/git/tags", tag_request, "tag")
    require(status == 201 and tag.get("tag") == ALLOCATION and tag.get("message") == message
            and tag.get("object", {}).get("type") == "commit"
            and tag["object"].get("sha") == head
            and type(tag.get("sha")) is str and re.fullmatch("[0-9a-f]{40}", tag["sha"]),
            "ISSUANCE_TAG_RESPONSE_UNKNOWN")
    request = dict(ref=REF, sha=tag["sha"])
    status, claimed = client.request("POST", "/git/refs", request, "ref")
    # This atomic operation, not the earlier absence read, chooses one winner.
    require(status == 201 and claimed.get("ref") == REF
            and claimed.get("object", {}).get("type") == "tag"
            and claimed["object"].get("sha") == tag["sha"],
            "ISSUANCE_REF_NOT_EXCLUSIVE_OR_UNKNOWN")
    status, current = client.request("GET", "/git/ref/tags/" + ALLOCATION, None, "readback")
    require(status == 200 and current.get("ref") == REF
            and current.get("object", {}).get("type") == "tag"
            and current["object"].get("sha") == tag["sha"], "ISSUANCE_READBACK_UNKNOWN")
    return dict(schema="bandido-fixed-allocation-issuance-v1", allocation=ALLOCATION,
                ref=REF, tag_sha=tag["sha"], head=head, run_id=run_id,
                run_attempt=attempt, seeds=list(range(1000491, 1000503)),
                root_intent=root_intent, status="ONE_ATOMIC_REF_CREATED_AND_READ_BACK")

def admit(control):
    require(os.environ.get("GITHUB_REPOSITORY") == REPO
            and os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
            and os.environ.get("GITHUB_ACTOR") == "carabinshely", "ISSUANCE_CALLER")
    body = os.environ.get("CURRENT_BODY", "")
    require(len(body) <= 8192 and body.count("PAIRED29_GO_JSON\n") == 1
            and body.count("\nPAIRED29_END") == 1, "ISSUANCE_BODY")
    go = json.loads(body.split("PAIRED29_GO_JSON\n", 1)[1].split("\nPAIRED29_END", 1)[0])
    require(type(go) is dict and set(go) ==
            {"subject", "go", "head", "driver_sha256", "manifest_sha256",
             "gate_sha256", "exhaustive_review", "adversarial_review",
             "root_intent", "first_issue_comment_id", "first_issue_nonce", "pr_number",
             "allocation_commit_sha"}
            and go.get("subject") == "paired29" and go.get("go") is True
            and go.get("head") == os.environ.get("HEAD_SHA") and
            type(go.get("pr_number")) is int and
            str(go["pr_number"]) == os.environ.get("PR_NUMBER"),
            "ISSUANCE_BODY_HEAD")
    token = os.environ.pop("ISSUANCE_TOKEN", "")
    client = Client(token, control)
    global_first = validate_global_preissue(client, head=go["head"],
        pr_number=go.get("pr_number"), root_intent=go.get("root_intent"),
        nonce=go.get("first_issue_nonce"),
        allocation_commit_sha=go.get("allocation_commit_sha"))
    first = validate_first_run(client, head=go["head"],
        run_id=os.environ.get("GITHUB_RUN_ID"), pr_number=go.get("pr_number"),
        root_intent=go.get("root_intent"), comment_id=go.get("first_issue_comment_id"),
        nonce=go.get("first_issue_nonce"),
        global_created_at=global_first["commit_created_at"])
    write_new(control / "issuance-global-preissue-validated.json", canonical(global_first))
    write_new(control / "issuance-first-run-validated.json", canonical(first))
    receipt = claim(client, go["head"], os.environ.get("GITHUB_RUN_ID"),
                    os.environ.get("GITHUB_RUN_ATTEMPT"), go.get("root_intent"))
    receipt["first_issue"] = first
    receipt["global_preissue"] = global_first
    write_new(control / "issuance-accepted.json", canonical(receipt))
    return receipt
