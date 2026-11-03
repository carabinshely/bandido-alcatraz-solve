"""One fixed allocation claim through GitHub's atomic Create-reference API.
Docs: https://docs.github.com/en/rest/git/refs#create-a-reference
      https://docs.github.com/en/rest/git/tags#create-a-tag-object
No project imports; network is permitted only inside the root-admitted CI driver.
"""
import json
import http.client
import os
import re
import urllib.error
import urllib.request

REPO = "carabinshely/bandido-alcatraz-solve"
BASE = "https://api.github.com/repos/" + REPO
ALLOCATION = "bandido-seeds-1000401-1000416"
REF = "refs/tags/" + ALLOCATION
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
        require((method, path, label) in (
            ("GET", "/git/ref/tags/" + ALLOCATION, "check"),
            ("POST", "/git/tags", "tag"),
            ("POST", "/git/refs", "ref"),
            ("GET", "/git/ref/tags/" + ALLOCATION, "readback")), "ISSUANCE_ENDPOINT")
        payload = None if data is None else canonical(data)
        require(payload is None or len(payload) <= 8192, "ISSUANCE_REQUEST_CAP")
        # Intent is durable before each distinct HTTP operation; never logs auth.
        write_new(self.control / ("issuance-" + label + "-request.json"),
                  canonical(dict(method=method, path=path, body=data)))
        req = urllib.request.Request(BASE + path, data=payload, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Accept-Encoding": "identity",
            "Accept": "application/vnd.github+json", "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "Bandido-fixed-issuance09"})
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

def claim(client, head, run_id, attempt, root_intent):
    require(type(head) is str and re.fullmatch("[0-9a-f]{40}", head), "ISSUANCE_HEAD")
    require(type(run_id) is str and re.fullmatch("[1-9][0-9]{0,19}", run_id), "ISSUANCE_RUN")
    require(attempt == "1", "ISSUANCE_ATTEMPT")
    require(type(root_intent) is str and 0 < len(root_intent) <= 256, "ISSUANCE_ROOT")
    status, old = client.request("GET", "/git/ref/tags/" + ALLOCATION, None, "check")
    require(status == 404, "ALLOCATION_ALREADY_ISSUED_OR_CHECK_NOT_404")
    message = canonical(dict(schema="bandido-fixed-allocation-issuance-v1",
        allocation=ALLOCATION, seeds=list(range(1000401, 1000417)), head=head,
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
                run_attempt=attempt, seeds=list(range(1000401, 1000417)),
                root_intent=root_intent, status="ONE_ATOMIC_REF_CREATED_AND_READ_BACK")

def admit(control):
    require(os.environ.get("GITHUB_REPOSITORY") == REPO
            and os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
            and os.environ.get("GITHUB_ACTOR") == "carabinshely", "ISSUANCE_CALLER")
    body = os.environ.get("CURRENT_BODY", "")
    require(len(body) <= 8192 and body.count("PAIRED09_GO_JSON\n") == 1
            and body.count("\nPAIRED09_END") == 1, "ISSUANCE_BODY")
    go = json.loads(body.split("PAIRED09_GO_JSON\n", 1)[1].split("\nPAIRED09_END", 1)[0])
    require(go.get("subject") == "paired09" and go.get("go") is True
            and go.get("head") == os.environ.get("HEAD_SHA"), "ISSUANCE_BODY_HEAD")
    token = os.environ.pop("ISSUANCE_TOKEN", "")
    receipt = claim(Client(token, control), go["head"], os.environ.get("GITHUB_RUN_ID"),
                    os.environ.get("GITHUB_RUN_ATTEMPT"), go.get("root_intent"))
    write_new(control / "issuance-accepted.json", canonical(receipt))
    return receipt

