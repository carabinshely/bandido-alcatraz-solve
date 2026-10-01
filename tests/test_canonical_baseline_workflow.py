"""Synthetic workflow safety checks; never invokes baseline computation."""
from pathlib import Path
import subprocess
import tempfile


def test_workflow_initializes_then_runs_once_with_upload_reserve():
    text=(Path(__file__).parents[1]/'.github/workflows/canonical-baseline.yml').read_text()
    assert 'types: [opened]' in text
    assert "PYTHONDONTWRITEBYTECODE: '1'" in text
    assert "python -m pip install 'pytest>=8.0'" in text
    assert "pip install -e" not in text
    assert "github.head_ref == 'research/worker29-canonical-baseline'" in text
    assert 'runs-on: [self-hosted, Linux, X64, bandido-alcatraz-ci]' in text
    assert 'timeout-minutes: 60' in text and '2400s python scripts/run_canonical_baseline.py run' in text
    assert text.index('run_canonical_baseline.py initialize') < text.index('actions/setup-python') < text.index('python -m pytest') < text.index('run_canonical_baseline.py run')
    assert text.count('if: always()')==2
    assert 'path: ${{ env.BASELINE_OUTPUT }}/' in text
    assert 'ref: ${{ github.event.pull_request.head.sha }}' in text


def test_normalized_sibling_output_survives_checkout_cleanup():
    with tempfile.TemporaryDirectory() as tmp:
        workspace=Path(tmp)/'repo';workspace.mkdir()
        subprocess.run(['git','init','-q',str(workspace)],check=True)
        output=subprocess.check_output(['realpath','-m',str(workspace/'..'/'bandido-canonical-baseline'/'123'/'1')],text=True).strip()
        assert '..' not in Path(output).parts
        out=Path(output);out.mkdir(parents=True);receipt=out/'receipt.json';receipt.write_text('evidence')
        subprocess.run(['git','clean','-ffdx'],cwd=workspace,check=True,capture_output=True)
        assert receipt.read_text()=='evidence'
