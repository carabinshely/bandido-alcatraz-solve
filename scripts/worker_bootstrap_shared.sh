#!/bin/bash
# Fixed shared startup extracted from Worker37. Source only; no implicit entry.
# Only the two bootstrap_*_prepare consumers are public. No argv/code callbacks.
_bootstrap_sanitize() {
  local bootstrap_name
  set +xv
  umask 077
  for bootstrap_name in ${!LD@} ${!PYTHON@}; do unset "$bootstrap_name"; done
  export LC_ALL=C
}

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


_bootstrap_paths_and_claim() {
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

durable_root=$RUNNER_TOOL_CACHE/$bootstrap_namespace
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
if [[ $bootstrap_consumer == worker37-preparation-v1 ]]; then
  printf 'schema=worker37-observed-reservation-v1\nallocation_id=%s\nrun_id=%s\nrun_attempt=1\nobserved_head=%s\ndescriptor_binding=not_yet_validated\npreparation_only=true\nmeasurement_admitted=false\n' "$allocation_id" "$GITHUB_RUN_ID" "$WORKER37_HEAD" > "$allocation_directory/reservation.txt" || block evidence_incomplete reservation_write
else
  printf 'schema=worker38-observed-reservation-v1\nallocation_id=%s\nrun_id=%s\nrun_attempt=1\nobserved_head=%s\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n' "$allocation_id" "$GITHUB_RUN_ID" "$WORKER38_HEAD" > "$allocation_directory/reservation.txt" || block execution_incomplete reservation_write
fi
sync_file_and_parent "$allocation_directory/reservation.txt" || block evidence_incomplete reservation_sync
attempt_directory=$allocation_directory/run-$GITHUB_RUN_ID-attempt-1
command mkdir -m 0700 -- "$attempt_directory" 2>/dev/null || block execution_blocked attempt_exists_or_race
owned_private_directory "$attempt_directory"
command sync -- "$allocation_directory" 2>/dev/null || block evidence_incomplete attempt_parent_sync

}

_bootstrap_runtime() {
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
[[ $checkout_head == "${!bootstrap_head_name}" && $checkout_tree =~ ^[0-9a-f]{40}$ ]] || block integrity_invalid checkout_identity
module=$GITHUB_WORKSPACE/$bootstrap_module
canonical_existing "$module"
[[ -f $module ]] || block execution_blocked module_missing

printf -v "${bootstrap_prefix}EXECUTABLE" '%s' "$executable"
printf -v "${bootstrap_prefix}LIBRARY" '%s' "$library"
printf -v "${bootstrap_prefix}EXECUTABLE_STAT" '%s' "$executable_after"
printf -v "${bootstrap_prefix}LIBRARY_STAT" '%s' "$library_after"
printf -v "${bootstrap_prefix}HEAD" '%s' "$checkout_head"
printf -v "${bootstrap_prefix}TREE" '%s' "$checkout_tree"
printf -v "${bootstrap_prefix}RUN_ID" '%s' "$GITHUB_RUN_ID"
printf -v "${bootstrap_prefix}PR_NUMBER" '%s' "$PR_NUMBER"
printf -v "${bootstrap_prefix}BRANCH" '%s' "${!bootstrap_branch_name}"
printf -v "${bootstrap_prefix}JOB" '%s' "${GITHUB_JOB-bootstrap}"
printf -v "${bootstrap_prefix}ALLOCATION_ID" '%s' "$allocation_id"
export "${bootstrap_prefix}EXECUTABLE" "${bootstrap_prefix}LIBRARY" "${bootstrap_prefix}EXECUTABLE_STAT" "${bootstrap_prefix}LIBRARY_STAT"
export "${bootstrap_prefix}HEAD" "${bootstrap_prefix}TREE" "${bootstrap_prefix}RUN_ID" "${bootstrap_prefix}PR_NUMBER" "${bootstrap_prefix}BRANCH" "${bootstrap_prefix}JOB" "${bootstrap_prefix}ALLOCATION_ID"

}

bootstrap_worker37_prepare() {
  (( $# == 0 )) || block execution_blocked unexpected_argument
  bootstrap_consumer=worker37-preparation-v1
  bootstrap_namespace=worker37-bootstrap-readiness
  bootstrap_prefix=WORKER37_
  bootstrap_head_name=WORKER37_HEAD
  bootstrap_branch_name=WORKER37_HEAD_REF
  bootstrap_module=scripts/worker37_bootstrap.py
  allocation_id=worker37-bootstrap-readiness-01
  expected_executable_sha256=a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc
  expected_library_sha256=ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896
  _bootstrap_sanitize
  _bootstrap_paths_and_claim
}

bootstrap_worker38_prepare() {
  (( $# == 0 )) || block execution_blocked unexpected_argument
  bootstrap_consumer=worker38-synthetic-profile-v1
  bootstrap_namespace=worker38-synthetic-profile
  bootstrap_prefix=WORKER38_
  bootstrap_head_name=WORKER38_HEAD
  bootstrap_branch_name=WORKER38_HEAD_REF
  bootstrap_module=scripts/worker38/admission.py
  allocation_id=worker38-synthetic-profile-01
  expected_executable_sha256=a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc
  expected_library_sha256=ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896
  _bootstrap_sanitize
  _bootstrap_paths_and_claim
}

_bootstrap_event_snapshot() {
canonical_existing "${GITHUB_EVENT_PATH-}"
[[ -f $GITHUB_EVENT_PATH ]] || block execution_blocked event_missing
event_before=$(stat_identity "$GITHUB_EVENT_PATH") || block evidence_incomplete event_stat
event_bytes=$(command stat -c '%s' -- "$GITHUB_EVENT_PATH" 2>/dev/null) || block evidence_incomplete event_stat
[[ $event_bytes =~ ^[0-9]{1,8}$ ]] || block resource_incomplete event_size
(( event_bytes <= 2097152 )) || block resource_incomplete event_size
event_source_digest=$(sha256_file "$GITHUB_EVENT_PATH") || block evidence_incomplete event_hash
event_snapshot=$attempt_directory/event.json
# The bound applies only to this copy subshell. It cannot change the Python
# leaf's inherited limits. A growing source can leave at most a 2MiB prefix.
if ! (
  trap - EXIT
  set +o posix
  event_copy_limit=$(ulimit -S -f)
  [[ $event_copy_limit == unlimited || ( $event_copy_limit =~ ^[0-9]+$ && $event_copy_limit -ge 2048 ) ]] || exit 1
  ulimit -S -f 2048 || exit 1
  command cat -- "$GITHUB_EVENT_PATH"
) > "$event_snapshot" 2>/dev/null; then
  block evidence_incomplete event_copy_incomplete
fi
event_after=$(stat_identity "$GITHUB_EVENT_PATH") || block evidence_incomplete event_stat
event_copy_bytes=$(command stat -c '%s' -- "$event_snapshot" 2>/dev/null) || block evidence_incomplete event_snapshot_stat
[[ $event_before == "$event_after" && $event_copy_bytes == "$event_bytes" ]] || block integrity_invalid event_changed
event_snapshot_before=$(stat_identity "$event_snapshot") || block evidence_incomplete event_snapshot_stat
event_snapshot_digest=$(sha256_file "$event_snapshot") || block evidence_incomplete event_snapshot_hash
event_snapshot_after=$(stat_identity "$event_snapshot") || block evidence_incomplete event_snapshot_stat
[[ $event_snapshot_before == "$event_snapshot_after" && $event_snapshot_digest == "$event_source_digest" ]] || block integrity_invalid event_snapshot_readback
sync_file_and_parent "$event_snapshot" || block evidence_incomplete event_snapshot_sync
printf 'event_size_bytes=%s\nevent_sha256=%s\nevent_stat=%s\nevent_file_and_directory_fsync=confirmed\nevent_descriptor_interpretation=not_yet_performed\n' "$event_copy_bytes" "$event_snapshot_digest" "$event_snapshot_after" >> "$attempt_directory/shell-prefix.txt" || block evidence_incomplete event_provenance_write
sync_file_and_parent "$attempt_directory/shell-prefix.txt" || block evidence_incomplete event_provenance_sync
printf -v "${bootstrap_prefix}EVENT_SHA256" '%s' "$event_snapshot_digest"
printf -v "${bootstrap_prefix}EVENT_STAT" '%s' "$event_snapshot_after"
printf -v "${bootstrap_prefix}EVENT_FSYNC_CONFIRMED" '%s' 1
export "${bootstrap_prefix}EVENT_SHA256" "${bootstrap_prefix}EVENT_STAT" "${bootstrap_prefix}EVENT_FSYNC_CONFIRMED"

}
