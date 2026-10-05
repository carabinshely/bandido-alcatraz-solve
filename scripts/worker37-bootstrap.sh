#!/bin/bash
# One preparation-only launcher. Invoke only through the frozen P02 workflow.
set +xv
set -euo pipefail
[[ $# == 0 ]] || { printf 'P02 execution_blocked unexpected_argument\n'; exit 1; }
source "${BASH_SOURCE[0]%/*}/worker_bootstrap_shared.sh"
_bootstrap_sanitize
# Keep the existing credential out of ordinary helper-command environments.
export -n GH_TOKEN worker37_api_token
worker37_api_token=${GH_TOKEN-}
unset GH_TOKEN
# Unexpected redirection/helper errors must not disclose host paths. Deliberate
# fixed diagnostics use stdout; Python's own bounded stderr has private custody.
exec 2>/dev/null

phase=P02
attempt_directory=
metadata_exit=not_started
terminal_error=none
allocation_id=worker37-bootstrap-readiness-01
expected_executable_sha256=a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc
expected_library_sha256=ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896

block() {
  terminal_error=$2
  printf '%s %s %s\n' "$phase" "$1" "$2"
  exit 1
}

# All diagnostic strings are fixed; no helper stderr, environment or host path
# is copied to the public log. The list is the complete external-command map.
for required_command in realpath readlink stat id mkdir cat sync sha256sum git timeout; do
  type -P "$required_command" >/dev/null || block execution_blocked required_command_missing
done

[[ ${GITHUB_REPOSITORY-} == carabinshely/bandido-alcatraz-solve ]] || block execution_blocked repository
[[ ${GITHUB_ACTOR-} == carabinshely && ${GITHUB_TRIGGERING_ACTOR-} == carabinshely ]] || block execution_blocked actor
[[ ${WORKER37_SENDER-} == carabinshely && ${WORKER37_PR_AUTHOR-} == carabinshely ]] || block execution_blocked sender
[[ ${GITHUB_SERVER_URL-} == https://github.com && ${GITHUB_API_URL-} == https://api.github.com ]] || block execution_blocked origin
[[ ${RUNNER_NAME-} == bandido-alcatraz-ci ]] || block execution_blocked runner
[[ ${GITHUB_EVENT_NAME-} == pull_request && ${WORKER37_EVENT_ACTION-} == edited && ${GITHUB_RUN_ATTEMPT-} == 1 ]] || block execution_blocked event_attempt
[[ ${GITHUB_RUN_ID-} =~ ^[1-9][0-9]*$ && ${PR_NUMBER-} =~ ^[1-9][0-9]*$ ]] || block execution_blocked identifier
[[ ${WORKER37_HEAD-} =~ ^[0-9a-f]{40}$ ]] || block execution_blocked head
[[ ${WORKER37_HEAD_REF-} == research/worker37-bootstrap-readiness && ${WORKER37_BASE_REF-} == main ]] || block execution_blocked branch
[[ ${WORKER37_BASE_HEAD-} == 2b00e0d1e76364ae287946f7c0e3dc2baac4653f ]] || block execution_blocked base
[[ ${WORKER37_HEAD_REPOSITORY-} == "$GITHUB_REPOSITORY" && ${WORKER37_BASE_REPOSITORY-} == "$GITHUB_REPOSITORY" ]] || block execution_blocked same_repository
[[ ${WORKER37_BODY_CHANGED-} == true && ${WORKER37_PREVIOUS_BODY-} != *WORKER37_ENGINEERING_ADMISSION* ]] || block execution_blocked first_marker

phase=P03
bootstrap_worker37_prepare

# Called once on an ordinary return, within the original outer deadline. A hard
# kill can prevent this trap; an absent record therefore remains absent.
finish() {
  local original_exit=$1 terminal_status=$1 name path bytes before after digest payload_digest payload_before payload_after
  local ordinary_bytes=0 terminal_bytes=0 payload_paths= inventory_lines=
  trap - EXIT
  set +e
  unset worker37_api_token GH_TOKEN
  for worker37_name in ${!LD@} ${!PYTHON@}; do unset "$worker37_name"; done
  umask 077
  [[ -n $attempt_directory ]] || return "$original_exit"
  printf 'schema=worker37-shell-terminal-v1\nphase=%s\nexit_status=%s\nmetadata_exit=%s\nerror=%s\nkill_137_cause=uncertain\npreparation_only=true\nmeasurement_admitted=false\nscientific_classification=null\nloader_environment=removed\nself_fsync=not_yet_confirmed\n' "$phase" "$original_exit" "$metadata_exit" "$terminal_error" > "$attempt_directory/shell-terminal.txt"
  if (( $? != 0 )) || ! sync_file_and_parent "$attempt_directory/shell-terminal.txt"; then
    printf 'P09 evidence_incomplete shell_terminal_sync\n'
    return 1
  fi
  printf 'shell_terminal_file_and_directory_fsync=confirmed\nconfirmation_file_self_fsync=not_self_attested\n' > "$attempt_directory/shell-fsync.txt"
  if (( $? != 0 )) || ! sync_file_and_parent "$attempt_directory/shell-fsync.txt"; then
    printf 'P09 evidence_incomplete shell_confirmation_sync\n'
    return 1
  fi
  # Explicit payload allowlist: no recursive directory upload or expanded ZIP.
  for name in reservation.txt shell-prefix.txt event.json request-context.json reservation-admission.json pull-request.json postmerge-ci.json review-exhaustive.json review-adversarial.json preflight-run.json preflight-artifact.json preflight.zip metadata.stdout metadata.stderr result.json inventory.json terminal.json shell-terminal.txt shell-fsync.txt; do
    path=$attempt_directory/$name
    [[ -e $path || -L $path ]] || continue
    if [[ ! -f $path || -L $path ]]; then
      printf 'P09 integrity_invalid payload_type\n'; return 1
    fi
    before=$(stat_identity "$path") || { printf 'P09 evidence_incomplete payload_stat\n'; return 1; }
    bytes=$(command stat -c '%s' -- "$path" 2>/dev/null) || return 1
    [[ $bytes =~ ^[0-9]{1,8}$ ]] || { printf 'P09 resource_incomplete payload_size\n'; return 1; }
    case $name in
      result.json|inventory.json|terminal.json|shell-terminal.txt|shell-fsync.txt) (( terminal_bytes += bytes ));;
      *) (( ordinary_bytes += bytes ));;
    esac
    (( ordinary_bytes <= 30408704 && terminal_bytes <= 1048576 )) || { printf 'P09 resource_incomplete payload_budget\n'; return 1; }
    sync_file_and_parent "$path" || { printf 'P09 evidence_incomplete payload_sync\n'; return 1; }
    digest=$(sha256_file "$path") || { printf 'P09 evidence_incomplete payload_hash\n'; return 1; }
    after=$(stat_identity "$path") || return 1
    [[ $before == "$after" ]] || { printf 'P09 integrity_invalid payload_changed\n'; return 1; }
    inventory_lines+="$digest $bytes $name"$'\n'
    payload_paths+="$path"$'\n'
  done
  printf '%s' "$inventory_lines" > "$attempt_directory/shell-payload.txt" || return 1
  bytes=$(command stat -c '%s' -- "$attempt_directory/shell-payload.txt" 2>/dev/null) || return 1
  [[ $bytes =~ ^[0-9]{1,8}$ ]] || return 1
  (( terminal_bytes += bytes ))
  (( terminal_bytes <= 1048576 && ordinary_bytes + terminal_bytes <= 31457280 )) || { printf 'P09 resource_incomplete payload_budget\n'; return 1; }
  sync_file_and_parent "$attempt_directory/shell-payload.txt" || { printf 'P09 evidence_incomplete payload_inventory_sync\n'; return 1; }
  payload_before=$(stat_identity "$attempt_directory/shell-payload.txt") || return 1
  payload_digest=$(sha256_file "$attempt_directory/shell-payload.txt") || return 1
  payload_after=$(stat_identity "$attempt_directory/shell-payload.txt") || return 1
  [[ $payload_before == "$payload_after" ]] || { printf 'P09 integrity_invalid payload_inventory_changed\n'; return 1; }
  payload_paths+="$attempt_directory/shell-payload.txt"$'\n'
  if [[ -n ${GITHUB_OUTPUT-} ]]; then
    # The runner consumes these control records; mask before the upload action
    # can display its resolved input. Private paths are never ordinary log data.
    printf '::add-mask::%s\n' "$RUNNER_TOOL_CACHE"
    printf '::add-mask::%s\n' "$attempt_directory"
    printf 'payload_paths<<WORKER37_PAYLOAD_PATHS\n%sWORKER37_PAYLOAD_PATHS\npayload_inventory_sha256=%s\npayload_ready=true\n' "$payload_paths" "$payload_digest" >> "$GITHUB_OUTPUT" || return 1
  fi
  printf 'P09 bounded_payload_confirmed provider_wrapper_unverified\n'
  return "$terminal_status"
}
trap 'worker37_exit=$?; finish "$worker37_exit"; exit $?' EXIT

# Copy only this allocation's small exclusive reservation, never an old claim.
command cat -- "$allocation_directory/reservation.txt" > "$attempt_directory/reservation.txt" 2>/dev/null || block evidence_incomplete reservation_copy
sync_file_and_parent "$attempt_directory/reservation.txt" || block evidence_incomplete reservation_copy_sync
printf 'schema=worker37-shell-prefix-v1\nphase=P03\nallocation_id=%s\nrun_id=%s\nrun_attempt=1\nreservation_file_and_directory_fsync=confirmed\nattempt_parent_fsync=confirmed\ndescriptor_binding=not_yet_validated\n' "$allocation_id" "$GITHUB_RUN_ID" > "$attempt_directory/shell-prefix.txt" || block evidence_incomplete prefix_write
sync_file_and_parent "$attempt_directory/shell-prefix.txt" || block evidence_incomplete prefix_sync

# Preserve the provider event before a cache/runtime failure can end this
# attempt. This is a bounded raw snapshot, not descriptor interpretation.
_bootstrap_event_snapshot

phase=P04
_bootstrap_runtime

# The owner descriptor is parsed and bound by the sole leaf Python. No shell
# JSON, metadata-dependent reservation claim or admission output is fabricated.
phase=P05
printf 'P05 metadata_started\n'
set +e
GH_TOKEN="$worker37_api_token" LD_LIBRARY_PATH="${library%/*}" PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 command timeout --foreground --signal=KILL 120s "$executable" -B -s "$module" --event "$event_snapshot" --output "$attempt_directory" --source "$GITHUB_WORKSPACE" > "$attempt_directory/metadata.stdout" 2> "$attempt_directory/metadata.stderr"
metadata_exit=$?
set -e
unset worker37_api_token
phase=P09
if (( metadata_exit == 137 )); then
  terminal_error=metadata_killed_cause_uncertain
elif (( metadata_exit != 0 )); then
  terminal_error=metadata_nonzero
elif [[ ! -f $attempt_directory/result.json || ! -f $attempt_directory/inventory.json || ! -f $attempt_directory/terminal.json ]]; then
  block evidence_incomplete metadata_terminal_missing
fi
exit "$metadata_exit"
