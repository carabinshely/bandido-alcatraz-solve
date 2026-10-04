#!/bin/bash
# One preparation-only launcher. Invoke only through the frozen P02 workflow.
set -euo pipefail
umask 077
for worker37_name in ${!LD@} ${!PYTHON@}; do
  unset "$worker37_name"
done
export LC_ALL=C
# Keep the existing credential out of ordinary helper-command environments.
export -n GH_TOKEN
worker37_api_token=${GH_TOKEN-}
unset GH_TOKEN

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

absolute_plain_path() {
  [[ $1 == /* && $1 != / && $1 != */ && $1 != *$'\n'* && $1 != *$'\r'* && $1 != *:* && $1 != *'/../'* && $1 != */.. && $1 != *'/./'* && $1 != */. && $1 != *'//'* ]]
}

canonical_existing() {
  local candidate=$1 resolved link_target
  absolute_plain_path "$candidate" || block execution_blocked invalid_path
  [[ ! -L $candidate ]] || block execution_blocked symlink_path
  # realpath rejects intermediate aliases too; readlink supplies an independent
  # canonical readback without executing the target.
  resolved=$(command realpath -e -- "$candidate" 2>/dev/null) || block execution_blocked unresolved_path
  link_target=$(command readlink -e -- "$candidate" 2>/dev/null) || block execution_blocked unresolved_path
  [[ $resolved == "$candidate" && $link_target == "$candidate" ]] || block execution_blocked path_alias
}

overlap() { [[ $1 == "$2" || $1 == "$2/"* || $2 == "$1/"* ]]; }

owned_private_directory() {
  local owner_mode
  canonical_existing "$1"
  [[ -d $1 ]] || block execution_blocked directory_type
  owner_mode=$(command stat -c '%u:%a' -- "$1" 2>/dev/null) || block execution_blocked directory_stat
  [[ $owner_mode == "$runner_uid:700" ]] || block execution_blocked directory_owner_mode
}

stat_identity() {
  command stat -c '%d:%i:%s:%Y' -- "$1" 2>/dev/null
}

sha256_file() {
  local digest_line
  digest_line=$(command sha256sum -- "$1" 2>/dev/null) || return 1
  [[ $digest_line =~ ^([0-9a-f]{64})[[:space:]] ]] || return 1
  printf '%s' "${BASH_REMATCH[1]}"
}

sync_file_and_parent() {
  command sync -- "$1" 2>/dev/null && command sync -- "${1%/*}" 2>/dev/null
}

phase=P03
canonical_existing "${RUNNER_TOOL_CACHE-}"
canonical_existing "${GITHUB_WORKSPACE-}"
canonical_existing "${RUNNER_TEMP-}"
[[ -d $RUNNER_TOOL_CACHE && -d $GITHUB_WORKSPACE && -d $RUNNER_TEMP ]] || block execution_blocked directory_type
overlap "$RUNNER_TOOL_CACHE" "$GITHUB_WORKSPACE" && block execution_blocked cache_workspace_overlap
overlap "$RUNNER_TOOL_CACHE" "$RUNNER_TEMP" && block execution_blocked cache_temp_overlap
overlap "$GITHUB_WORKSPACE" "$RUNNER_TEMP" && block execution_blocked workspace_temp_overlap
runner_uid=$(command id -u 2>/dev/null) || block execution_blocked runner_uid
[[ $runner_uid =~ ^[0-9]+$ ]] || block execution_blocked runner_uid
storage_stats=$(command stat -f -c '%a:%S' -- "$RUNNER_TOOL_CACHE" 2>/dev/null) || block execution_blocked storage_stat
[[ $storage_stats =~ ^([0-9]{1,15}):([0-9]{1,9})$ ]] || block execution_blocked storage_stat
free_blocks=${BASH_REMATCH[1]}
block_bytes=${BASH_REMATCH[2]}
[[ $block_bytes != 0 && $block_bytes =~ ^[1-9][0-9]*$ ]] || block execution_blocked storage_stat
# Division avoids overflowing the product of provider-supplied counters.
(( free_blocks >= (1073741824 + block_bytes - 1) / block_bytes )) || block execution_blocked free_storage

durable_root=$RUNNER_TOOL_CACHE/worker37-bootstrap-readiness
for private_directory in "$durable_root" "$durable_root/allocations"; do
  if [[ ! -e $private_directory && ! -L $private_directory ]]; then
    command mkdir -m 0700 -- "$private_directory" 2>/dev/null || block execution_blocked directory_create
  fi
  owned_private_directory "$private_directory"
done
allocation_directory=$durable_root/allocations/$allocation_id
command mkdir -m 0700 -- "$allocation_directory" 2>/dev/null || block execution_blocked allocation_exists_or_race
owned_private_directory "$allocation_directory"
command sync -- "$durable_root/allocations" 2>/dev/null || block evidence_incomplete allocation_parent_sync
set -o noclobber
printf 'schema=worker37-observed-reservation-v1\nallocation_id=%s\nrun_id=%s\nrun_attempt=1\nobserved_head=%s\ndescriptor_binding=not_yet_validated\npreparation_only=true\nmeasurement_admitted=false\n' "$allocation_id" "$GITHUB_RUN_ID" "$WORKER37_HEAD" > "$allocation_directory/reservation.txt" || block evidence_incomplete reservation_write
sync_file_and_parent "$allocation_directory/reservation.txt" || block evidence_incomplete reservation_sync
attempt_directory=$allocation_directory/run-$GITHUB_RUN_ID-attempt-1
command mkdir -m 0700 -- "$attempt_directory" 2>/dev/null || block execution_blocked attempt_exists_or_race
owned_private_directory "$attempt_directory"
command sync -- "$allocation_directory" 2>/dev/null || block evidence_incomplete attempt_parent_sync

# Called once on an ordinary return, within the original outer deadline. A hard
# kill can prevent this trap; an absent record therefore remains absent.
finish() {
  local original_exit=$1 terminal_status=$1 name path bytes before after digest
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
  payload_paths+="$attempt_directory/shell-payload.txt"$'\n'
  if [[ -n ${GITHUB_OUTPUT-} ]]; then
    # The runner consumes these control records; mask before the upload action
    # can display its resolved input. Private paths are never ordinary log data.
    printf '::add-mask::%s\n' "$RUNNER_TOOL_CACHE"
    printf '::add-mask::%s\n' "$attempt_directory"
    printf 'payload_paths<<WORKER37_PAYLOAD_PATHS\n%sWORKER37_PAYLOAD_PATHS\npayload_ready=true\n' "$payload_paths" >> "$GITHUB_OUTPUT" || return 1
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

phase=P04
executable=$RUNNER_TOOL_CACHE/Python/3.11.16/x64/bin/python3.11
library=$RUNNER_TOOL_CACHE/Python/3.11.16/x64/lib/libpython3.11.so.1.0
canonical_existing "$executable"
canonical_existing "$library"
[[ -f $executable && -x $executable && -f $library ]] || block execution_blocked runtime_missing
executable_before=$(stat_identity "$executable") || block execution_blocked executable_stat
library_before=$(stat_identity "$library") || block execution_blocked library_stat
[[ $executable_before =~ ^[0-9]+:[0-9]+:[0-9]+:[0-9]+$ && $library_before =~ ^[0-9]+:[0-9]+:23041360:[0-9]+$ ]] || block execution_blocked runtime_stat
executable_digest=$(sha256_file "$executable") || block execution_blocked executable_hash
library_digest=$(sha256_file "$library") || block execution_blocked library_hash
executable_after=$(stat_identity "$executable") || block execution_blocked executable_stat
library_after=$(stat_identity "$library") || block execution_blocked library_stat
[[ $executable_before == "$executable_after" && $library_before == "$library_after" ]] || block integrity_invalid runtime_changed
[[ $executable_digest == "$expected_executable_sha256" ]] || block execution_blocked executable_hash_mismatch
[[ $library_digest == "$expected_library_sha256" ]] || block execution_blocked library_hash_mismatch

checkout_head=$(command git -C "$GITHUB_WORKSPACE" rev-parse --verify HEAD 2>/dev/null) || block execution_blocked checkout_head
checkout_tree=$(command git -C "$GITHUB_WORKSPACE" rev-parse --verify 'HEAD^{tree}' 2>/dev/null) || block execution_blocked checkout_tree
[[ $checkout_head == "$WORKER37_HEAD" && $checkout_tree =~ ^[0-9a-f]{40}$ ]] || block integrity_invalid checkout_identity
module=$GITHUB_WORKSPACE/scripts/worker37_bootstrap.py
canonical_existing "$module"
[[ -f $module ]] || block execution_blocked module_missing
canonical_existing "${GITHUB_EVENT_PATH-}"
[[ -f $GITHUB_EVENT_PATH ]] || block execution_blocked event_missing

export WORKER37_EXECUTABLE=$executable WORKER37_LIBRARY=$library
export WORKER37_EXECUTABLE_STAT=$executable_after WORKER37_LIBRARY_STAT=$library_after
export WORKER37_HEAD=$checkout_head WORKER37_TREE=$checkout_tree
export WORKER37_RUN_ID=$GITHUB_RUN_ID WORKER37_PR_NUMBER=$PR_NUMBER
export WORKER37_BRANCH=$WORKER37_HEAD_REF WORKER37_JOB=${GITHUB_JOB-bootstrap}
export WORKER37_ALLOCATION_ID=$allocation_id
# The owner descriptor is parsed and bound by the sole leaf Python. No shell
# JSON, metadata-dependent reservation claim or admission output is fabricated.
phase=P05
printf 'P05 metadata_started\n'
set +e
GH_TOKEN="$worker37_api_token" LD_LIBRARY_PATH="${library%/*}" PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 command timeout --foreground --signal=KILL 120s "$executable" -B -s "$module" --event "$GITHUB_EVENT_PATH" --output "$attempt_directory" --source "$GITHUB_WORKSPACE" > "$attempt_directory/metadata.stdout" 2> "$attempt_directory/metadata.stderr"
metadata_exit=$?
set -e
unset worker37_api_token
phase=P09
if (( metadata_exit == 137 )); then
  terminal_error=metadata_killed_cause_uncertain
elif (( metadata_exit != 0 )); then
  terminal_error=metadata_nonzero
fi
exit "$metadata_exit"
