"""Build the reviewable inline-only workflow from the standalone inspection source."""
from pathlib import Path
root=Path(__file__).resolve().parent
source=(root/'inspect_worker35_recovery.py').read_text()
source=source.rsplit('if __name__ == "__main__":',1)[0]
bootstrap=r'''
# GitHub metadata/bootstrap only. No checkout or project dependency imports.
import sys
import urllib.request
import signal

def api(path):
    require(path.startswith('/repos/' + REPOSITORY + '/actions/'), 'unexpected API path')
    request = urllib.request.Request('https://api.github.com' + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    require(len(raw) <= 2 * 1024 * 1024, 'API metadata exceeded bound')
    return parse_object(raw)

require(os.environ.get('GITHUB_EVENT_NAME') == 'push', 'recovery requires exact-branch push')
require(os.environ.get('GITHUB_REF') == 'refs/heads/research/worker35-evidence-recovery-36990202101', 'wrong recovery branch')
require(os.environ.get('GITHUB_ACTOR') == 'carabinshely', 'wrong recovery actor')
require(os.environ.get('GITHUB_RUN_ATTEMPT') == '1', 'recovery rerun not authorized')
require(os.environ.get('RUNNER_NAME') == RUNNER, 'wrong recovery runner')
new_run = os.environ['GITHUB_RUN_ID']
require(new_run.isdecimal() and new_run != str(RUN_ID), 'invalid independent recovery identity')
workspace = no_symlink_path(Path(os.environ['GITHUB_WORKSPACE']))
base = no_symlink_path(workspace.parent / 'bandido-worker35-evidence-recovery' / new_run / '1')
base_fd = open_directory(base, create=True)
with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
    stream.write('artifact_path=' + str(base) + '\n')
bootstrap_report = {'schema': 'worker35-recovery-bootstrap-v1', 'started_at': utc(),
    'original_run_id': RUN_ID, 'original_attempt': ATTEMPT, 'recovery_run_id': new_run,
    'recovery_run_attempt': '1', 'recovery_head': os.environ['GITHUB_SHA'],
    'authorization_url': AUTHORIZATION, 'mode': 'metadata-only', 'status': 'metadata_unavailable',
    'classification': None, 'research_interpretation_performed': False}
exit_code = 1
def inspection_timeout(signum, frame):
    raise InspectionDeadline('metadata inspection deadline reached')
signal.signal(signal.SIGALRM, inspection_timeout)
signal.alarm(300)
try:
    prefix = '/repos/' + REPOSITORY + '/actions/'
    run = api(prefix + 'runs/' + str(RUN_ID))
    job = api(prefix + 'jobs/' + str(JOB_ID))
    current = api(prefix + 'runs/' + new_run + '/jobs?filter=latest&per_page=100')
    matching = [j for j in current.get('jobs', []) if j.get('name') == 'metadata-recovery'
                and j.get('run_id') == int(new_run) and j.get('status') == 'in_progress']
    require(len(matching) == 1, 'recovery job identity unavailable')
    current_job = matching[0]
    require(current_job['runner_name'] == RUNNER and current_job.get('head_sha') == os.environ['GITHUB_SHA'],
            'recovery job runner/source mismatch')
    require(current_job.get('run_attempt') == 1, 'wrong recovery job attempt')
    metadata = {'run': run, 'job': job, 'recovery_job': current_job, 'fetched_at': utc()}
    write_new(base / 'authenticated-actions-metadata.json', canonical(metadata), directory_fd=base_fd)
    # The metadata inspector receives no credential or external-service handle.
    os.environ.pop('GH_TOKEN', None)
    result = inspect(workspace, base / 'inspection', metadata, current_job['runner_id'])
    bootstrap_report['status'] = result['status']
    exit_code = 1 if result['status'] == 'inspection_blocked' else 0
except Exception as error:
    bootstrap_report['status'] = 'metadata_inspection_blocked'
    bootstrap_report['blocker_type'] = type(error).__name__
finally:
    signal.alarm(0)
    os.environ.pop('GH_TOKEN', None)
    bootstrap_report['finished_at'] = utc()
    write_new(base / 'bootstrap-receipt.json', canonical(bootstrap_report), directory_fd=base_fd)
    # Metadata is limited to <30 MiB before upload; no truncation or cleanup.
    no_symlink_path(base)
    require(base.lstat().st_ino == os.fstat(base_fd).st_ino and base.lstat().st_dev == os.fstat(base_fd).st_dev,
            'recovery upload directory identity changed')
    upload_inventory = inventory(base)
    require(all(row['type'] in ('directory', 'file') for row in upload_inventory.values()),
            'recovery upload tree contains unsafe entries')
    total = sum(row['size_bytes'] for row in upload_inventory.values() if row['type'] == 'file')
    os.close(base_fd)
    if total >= 30 * 1024 * 1024:
        print('Metadata package exceeds 30 MiB; preserve local files and fail closed')
        exit_code = 1
    else:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('upload_safe=true\n')
print(json.dumps({'status': bootstrap_report['status'], 'mode': 'metadata-only',
                  'quiescence_proven': False, 'packaging_performed': False}))
raise SystemExit(exit_code)
'''
header='''name: Worker35 evidence recovery metadata only

on:
  push:
    branches: [research/worker35-evidence-recovery-36990202101]

permissions:
  contents: read
  actions: read

concurrency:
  group: worker35-evidence-recovery-36990202101
  cancel-in-progress: false

jobs:
  metadata-recovery:
    if: >-
      github.repository == 'carabinshely/bandido-alcatraz-solve' &&
      github.actor == 'carabinshely' && github.run_attempt == 1
    runs-on: [self-hosted, Linux, X64, bandido-alcatraz-ci]
    timeout-minutes: 10
    defaults:
      run:
        shell: bash
        working-directory: ${{ runner.temp }}
    steps:
      - name: Inspect original attempt metadata without checkout or research
        id: inspect
        env:
          GH_TOKEN: ${{ github.token }}
          PYTHONDONTWRITEBYTECODE: '1'
        run: |
          set -euo pipefail
          python3 -I -B - <<'PY'
'''
footer='''          PY
      - name: Upload bounded recovery metadata even if inspection is blocked
        if: always() && steps.inspect.outputs.upload_safe == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: worker35-recovery-metadata-${{ github.run_id }}-${{ github.run_attempt }}
          path: ${{ steps.inspect.outputs.artifact_path }}
          if-no-files-found: error
          compression-level: 0
          retention-days: 7
'''
body=''.join('          '+line+'\n' for line in (source+bootstrap).splitlines())
(root/'worker35-evidence-recovery.yml').write_text(header+body+footer)
print('Created inline-only workflow draft')
