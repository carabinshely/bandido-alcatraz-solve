"""Synthetic workflow safety checks; never invokes baseline computation."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile


def test_workflow_initializes_then_runs_once_with_upload_reserve():
    text=(Path(__file__).parents[1]/'.github/workflows/equipment-opportunity-development.yml').read_text()
    assert 'types: [opened, synchronize]' in text
    assert "PYTHONDONTWRITEBYTECODE: '1'" in text
    assert "PYTHONPYCACHEPREFIX: ''" in text
    assert "python -m pip install 'pytest>=8.0'" in text
    assert "pip install -e" not in text
    assert "github.head_ref == 'research/worker31-equipment-opportunity'" in text
    assert 'PREREGISTRATION_URL: https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5928556762' in text
    assert 'worker31-equipment-opportunity-${{ github.run_id }}-${{ github.run_attempt }}' in text
    assert 'runs-on: [self-hosted, Linux, X64, bandido-alcatraz-ci]' in text
    assert 'timeout-minutes: 60' in text and '2700s python scripts/run_equipment_opportunity_development.py run' in text
    assert text.index('run_equipment_opportunity_development.py initialize') < text.index('actions/setup-python') < text.index('python -m pytest') < text.index('run_equipment_opportunity_development.py run')
    assert text.count('if: always()')==2
    assert 'path: ${{ steps.evidence.outputs.upload_path }}/' in text
    assert 'ref: ${{ github.event.pull_request.head.sha }}' in text


def test_workflow_empty_cache_prefix_disables_inherited_external_cache():
    env = {**os.environ, 'PYTHONPYCACHEPREFIX': '', 'PYTHONDONTWRITEBYTECODE': '1'}
    subprocess.run([sys.executable, '-c',
                    'import sys; assert sys.pycache_prefix is None; assert sys.dont_write_bytecode'],
                   env=env, check=True)


def test_normalized_sibling_output_survives_checkout_cleanup():
    with tempfile.TemporaryDirectory() as tmp:
        workspace=Path(tmp)/'repo';workspace.mkdir()
        subprocess.run(['git','init','-q',str(workspace)],check=True)
        output=subprocess.check_output(['realpath','-m',str(workspace/'..'/'bandido-equipment-development'/'123'/'1')],text=True).strip()
        assert '..' not in Path(output).parts
        out=Path(output);out.mkdir(parents=True);receipt=out/'receipt.json';receipt.write_text('evidence')
        subprocess.run(['git','clean','-ffdx'],cwd=workspace,check=True,capture_output=True)
        assert receipt.read_text()=='evidence'



def test_workflow_retains_fixed_compute_kill_and_finalization_upload_budget():
    import re
    text = (Path(__file__).parents[1] / '.github/workflows/equipment-opportunity-development.yml').read_text()
    assert 'timeout --signal=TERM --kill-after=30s 2700s' in text
    assert 'timeout-minutes: 46' in text
    assert 'types: [opened, synchronize]' in text and 'workflow_dispatch' not in text
    budgets = [int(value) for value in re.findall(r'^        timeout-minutes: (\d+)$', text, re.MULTILINE)]
    assert sum(budgets) <= 60
    assert "tempfile.mkstemp(prefix='infrastructure-blocker-'" in text
    assert 'persist-credentials: false' in text
    assert 'fetch-depth: 0' in text


def workflow_shell_step(name):
    text = (Path(__file__).parents[1] / '.github/workflows/equipment-opportunity-development.yml').read_text()
    step = text.split(f'      - name: {name}\n', 1)[1].split('\n      - ', 1)[0]
    code = step.split('        run: |\n', 1)[1]
    return '\n'.join(line[10:] if line.startswith('          ') else line for line in code.splitlines())


def test_failed_output_initialization_uses_independent_bounded_fallback(tmp_path):
    workspace = tmp_path / 'checkout'
    workspace.mkdir()
    (workspace / 'unrelated.txt').write_text('must never upload this')
    runner_temp = tmp_path / 'runner-temp'
    runner_temp.mkdir()
    outputs = tmp_path / 'step-output'
    outputs.write_text('')
    expected = workspace.parent / 'bandido-equipment-development/123/2'
    env = {**os.environ, 'RUNNER_TEMP': str(runner_temp), 'GITHUB_RUN_ID': '123',
           'GITHUB_RUN_ATTEMPT': '2', 'GITHUB_WORKSPACE': str(workspace), 'RUNNER_NAME': 'bandido-alcatraz-ci',
           'DEVELOPMENT_OUTPUT': '', 'GITHUB_OUTPUT': str(outputs), 'EXPECTED_HEAD': 'a' * 40}
    initial = subprocess.run(['bash', '-c', workflow_shell_step('Durable normalized output path')],
                             cwd=workspace, env=env, capture_output=True, text=True)
    assert initial.returncode != 0 and outputs.read_text() == ''
    finalizer = workflow_shell_step('Reconcile final status').replace("${{ steps.tests.outcome }}", 'skipped').replace("${{ steps.cohort.outcome }}", 'skipped')
    result = subprocess.run(['bash', '-c', finalizer], cwd=workspace, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert dict(line.split('=', 1) for line in outputs.read_text().splitlines()) == {'upload_path': str(expected), 'safe': 'true'}
    assert len(list(expected.glob('infrastructure-blocker-*.json'))) == 1
    assert not (workspace / 'receipt.json').exists()
    assert (workspace / 'unrelated.txt').read_text() == 'must never upload this'
    text = (Path(__file__).parents[1] / '.github/workflows/equipment-opportunity-development.yml').read_text()
    assert "if: always() && steps.evidence.outputs.safe == 'true'" in text
    assert 'path: ${{ steps.evidence.outputs.upload_path }}/' in text
    assert 'path: ${{ env.DEVELOPMENT_OUTPUT }}' not in text
    assert 'runner.temp' not in text and 'RUNNER_TEMP' not in text
    # The actual published upload destination survives both cleanup domains.
    import shutil
    preserved = {path.name: path.read_bytes() for path in expected.iterdir()}
    shutil.rmtree(runner_temp)
    shutil.rmtree(workspace)
    assert {path.name: path.read_bytes() for path in expected.iterdir()} == preserved


def test_failed_fallback_path_validation_cannot_enable_upload(tmp_path):
    workspace = tmp_path / 'checkout'
    workspace.mkdir()
    outputs = tmp_path / 'step-output'
    outputs.write_text('')
    env = {**os.environ, 'RUNNER_TEMP': '/', 'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '2',
           'GITHUB_WORKSPACE': '/', 'GITHUB_OUTPUT': str(outputs)}
    result = subprocess.run(['bash', '-c', workflow_shell_step('Reconcile final status')], cwd=workspace,
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert outputs.read_text() == ''
    assert list(workspace.iterdir()) == []


def test_research_preflight_is_focused_and_routine_ci_keeps_full_suite():
    root = Path(__file__).parents[1]
    research = (root / '.github/workflows/equipment-opportunity-development.yml').read_text()
    command = 'python -m pytest -q tests/test_equipment_opportunity.py tests/test_equipment_development_harness.py tests/test_equipment_development_workflow.py'
    assert f'run: {command}\n' in research
    assert 'name: Worker31 focused synthetic tests\n        id: tests\n        timeout-minutes: 3' in research
    assert '        run: python -m pytest -q\n' not in research
    routine = (root / '.github/workflows/test.yml').read_text()
    assert 'run: python -m pytest -q\n' in routine
