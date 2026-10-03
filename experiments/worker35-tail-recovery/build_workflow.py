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
    source = (ROOT / 'recover_tails.py').read_text()
    def mode_tree(mode):
        tree = ast.parse(source)
        if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
            tree.body.pop(0)
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        branch = next(n for n in main.body if isinstance(n, ast.If))
        verify = branch.orelse[0]
        if mode == 'verify':
            branch.test, branch.body = verify.test, verify.body
        branch.orelse = verify.orelse
        return tree
    tree = mode_tree('snapshot')
    tree.body = [n for n in tree.body if not isinstance(n, ast.FunctionDef) or n.name != 'verify_upload']
    snapshot_code = run_block(ast.unparse(tree))
    tree = mode_tree('verify')
    omitted = {'snapshot_tails', 'capture_upload', 'relative_parts', 'relative_parent', 'tree_inventory', 'hash_one', 'validate_original'}
    tree.body = [n for n in tree.body if not isinstance(n, ast.FunctionDef) or n.name not in omitted]
    verify_code = run_block(ast.unparse(tree))
    base = {'GH_TOKEN': '${{ github.token }}', 'EXPECTED_JOB_NAME': 'tail-preservation', 'PYTHONDONTWRITEBYTECODE': '1'}
    snapshot_env = {**base, 'RECOVERY_MODE': 'snapshot'}
    verify_env = {**base, 'RECOVERY_MODE': 'verify',
                  'EXPECTED_UPLOAD_RECORDS': '${{ steps.snapshot.outputs.upload_records }}',
                  'EXPECTED_UPLOAD_LOCATIONS': '${{ steps.snapshot.outputs.upload_locations }}'}
    paths = '\n'.join('${{ steps.snapshot.outputs.upload_path }}/' + name for name in (
        'source-manifest.json', 'authenticated-actions-metadata.json', 'source-inventory.json', 'recovery-report.json',
        'call-results-pass-2-1000319.jsonl', 'decision-traces-pass-2-1000319.jsonl', 'resource-metrics.jsonl'))
    steps = [
        {'name': 'Snapshot three raw tails and verify full raw hash inventory', 'id': 'snapshot',
         'working-directory': '${{ runner.temp }}', 'shell': 'bash', 'env': snapshot_env, 'run': snapshot_code},
        {'name': 'Check local preservation bytes before upload', 'id': 'verify', 'if': "always() && steps.snapshot.outputs.upload_ready == 'true'",
         'working-directory': '${{ runner.temp }}', 'shell': 'bash', 'env': verify_env, 'run': verify_code},
        {'name': 'Preserve three files and bounded recovery metadata', 'if': "always() && steps.verify.outcome == 'success'",
         'uses': 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
         'with': {'name': 'worker35-tail-preservation-${{ github.run_id }}-1', 'path': paths,
                  'if-no-files-found': 'error', 'compression-level': 0, 'retention-days': 7}},
        {'name': 'Recheck local preservation bytes after upload', 'if': "always() && steps.verify.outcome == 'success'",
         'working-directory': '${{ runner.temp }}', 'shell': 'bash', 'env': verify_env, 'run': verify_code}]
    workflow = {'name': 'Worker35 preserve three raw tail files',
        'on': {'push': {'branches': ['research/worker35-tail-recovery-36990202101']}},
        'permissions': {'contents': 'read', 'actions': 'read'},
        'concurrency': {'group': 'worker35-tail-recovery-36990202101', 'cancel-in-progress': False},
        'jobs': {'preserve': {'name': 'tail-preservation',
            'if': "github.repository == 'carabinshely/bandido-alcatraz-solve' && github.actor == 'carabinshely' && github.run_attempt == 1",
            'runs-on': ['self-hosted', 'Linux', 'X64', 'bandido-alcatraz-ci'], 'timeout-minutes': 15, 'steps': steps}}}
    class Dumper(yaml.SafeDumper):
        pass
    def string(dumper, value):
        return dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None)
    Dumper.add_representer(str, string)
    target = ROOT / 'worker35-tail-recovery.yml'
    target.write_text(yaml.dump(workflow, Dumper=Dumper, sort_keys=False, width=120))
    assert yaml.safe_load(target.read_text()) == workflow
    print(f'Rendered workflow: snapshot run {len(snapshot_code)}, verification run {len(verify_code)} characters')


if __name__ == '__main__':
    build()
