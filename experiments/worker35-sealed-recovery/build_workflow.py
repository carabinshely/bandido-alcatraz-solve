"""Render reviewable inline recovery; no checkout and no remote script imports."""
import ast
import io
from pathlib import Path
import tokenize
import yaml

ROOT = Path(__file__).resolve().parent


def compact(source):
    tree = ast.parse(source)
    text = ast.unparse(tree)
    inside_string = set()
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.STRING and token.end[0] > token.start[0]:
            inside_string.update(range(token.start[0] + 1, token.end[0] + 1))
    lines = []
    for n, line in enumerate(text.splitlines(), 1):
        if n not in inside_string:
            spaces = len(line) - len(line.lstrip(" "))
            assert spaces % 4 == 0
            line = " " * (spaces // 4) + line.lstrip(" ")
        lines.append(line)
    result = "\n".join(lines) + "\n"
    assert ast.dump(tree, include_attributes=False) == ast.dump(ast.parse(result), include_attributes=False)
    return result


def run_block(source):
    result = "set -euo pipefail\npython3 -I -B - <<'PY'\n" + compact(source) + "PY\n"
    assert len(result) <= 21000, ("GitHub run block exceeds limit", len(result))
    return result


def build():
    source = (ROOT / "recover_sealed.py").read_text()
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if not isinstance(node, ast.FunctionDef) or node.name not in {"check_part", "check_metadata"}]
    full = run_block(ast.unparse(tree))
    tree = ast.parse(source)
    omitted = {"snapshot", "seal_metadata", "validate_original", "source_metadata", "manifest_check", "hash_record"}
    tree.body = [node for node in tree.body if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name not in omitted]
    part_code = run_block(ast.unparse(tree))
    upload = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
    runner = ["self-hosted", "Linux", "X64", "bandido-alcatraz-ci"]
    job_if = "github.repository == 'carabinshely/bandido-alcatraz-solve' && github.actor == 'carabinshely' && github.run_attempt == 1"
    base_env = {"GH_TOKEN": "${{ github.token }}", "PYTHONDONTWRITEBYTECODE": "1"}
    snapshot_env = {**base_env, "RECOVERY_MODE": "snapshot", "EXPECTED_JOB_NAME": "sealed-snapshot"}
    part_env = {**base_env, "RECOVERY_MODE": "part", "EXPECTED_JOB_NAME": "upload-${{ matrix.part }}",
                "SELECTED_PART": "${{ matrix.part }}", "EXPECTED_REPORT_SHA": "${{ needs.snapshot.outputs.report_sha }}"}
    metadata_env = {**base_env, "RECOVERY_MODE": "metadata", "EXPECTED_JOB_NAME": "sealed-snapshot",
                    "EXPECTED_METADATA_RECORDS": "${{ steps.snapshot.outputs.metadata_records }}",
                    "EXPECTED_METADATA_STAT": "${{ steps.snapshot.outputs.metadata_stat }}"}
    metadata_paths = "\n".join("${{ steps.snapshot.outputs.metadata_path }}/" + name for name in (
        "artifact-manifest.json", "original-receipt.json", "original-admission.json",
        "authenticated-actions-metadata.json", "recovery-report.json", "blocked-report.json"))
    snapshot = {
        "name": "sealed-snapshot", "if": job_if, "runs-on": runner, "timeout-minutes": 15,
        "outputs": {"parts": "${{ steps.snapshot.outputs.parts }}", "report_sha": "${{ steps.snapshot.outputs.report_sha }}"},
        "steps": [
            {"name": "Snapshot original sealed bytes with stable hash and identity gates", "id": "snapshot",
             "working-directory": "${{ runner.temp }}", "shell": "bash", "env": snapshot_env, "run": full},
            {"name": "Verify metadata bytes and stamps before upload", "id": "metaverify", "if": "always() && steps.snapshot.outputs.metadata_ready == 'true'",
             "working-directory": "${{ runner.temp }}", "shell": "bash", "env": metadata_env, "run": part_code},
            {"name": "Preserve bounded recovery metadata and contradictions", "if": "always() && steps.metaverify.outcome == 'success'", "uses": upload,
             "with": {"name": "worker35-sealed-recovery-metadata-${{ github.run_id }}-1", "path": metadata_paths,
                      "if-no-files-found": "error", "compression-level": 0, "retention-days": 7}},
            {"name": "Recheck metadata bytes and stamps after upload", "if": "always() && steps.metaverify.outcome == 'success'",
             "working-directory": "${{ runner.temp }}", "shell": "bash", "env": metadata_env, "run": part_code}]}
    upload_job = {
        "name": "upload-${{ matrix.part }}", "needs": "snapshot", "if": job_if + " && needs.snapshot.result == 'success'",
        "strategy": {"fail-fast": False, "max-parallel": 1, "matrix": {"part": "${{ fromJSON(needs.snapshot.outputs.parts) }}"}},
        "runs-on": runner, "timeout-minutes": 5,
        "steps": [
            {"name": "Verify copied part and original registered runner before upload", "id": "verify",
             "working-directory": "${{ runner.temp }}", "shell": "bash", "env": part_env, "run": part_code},
            {"name": "Upload one bounded sealed part", "uses": upload,
             "with": {"name": "worker35-sealed-${{ github.run_id }}-1-${{ matrix.part }}", "path": "${{ steps.verify.outputs.part_path }}",
                      "if-no-files-found": "error", "compression-level": 0, "retention-days": 7}},
            {"name": "Recheck copied part hash after upload", "if": "always() && steps.verify.outcome == 'success'",
             "working-directory": "${{ runner.temp }}", "shell": "bash", "env": part_env, "run": part_code}]}
    workflow = {"name": "Worker35 preserve existing sealed transport",
                "on": {"push": {"branches": ["research/worker35-sealed-recovery-36990202101"]}},
                "permissions": {"contents": "read", "actions": "read"},
                "concurrency": {"group": "worker35-sealed-recovery-36990202101", "cancel-in-progress": False},
                "jobs": {"snapshot": snapshot, "upload-part": upload_job}}
    class Dumper(yaml.SafeDumper):
        pass
    def string(dumper, value):
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|" if "\n" in value else None)
    Dumper.add_representer(str, string)
    target = ROOT / "worker35-sealed-recovery.yml"
    target.write_text(yaml.dump(workflow, Dumper=Dumper, sort_keys=False, width=120))
    assert yaml.safe_load(target.read_text()) == workflow
    print(f"Rendered workflow: snapshot run {len(full)}, part run {len(part_code)} characters")


if __name__ == "__main__":
    build()
