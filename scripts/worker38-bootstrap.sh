#!/bin/bash
# Closed Worker38 startup, admission, measurement and original-cutoff preservation.
# Internal fixed functions are sourced only by the literal commands below.
set +xv
set -euo pipefail
source "${BASH_SOURCE[0]%/*}/worker_bootstrap_shared.sh"

block() {
  local classification=$1
  [[ $classification != evidence_incomplete ]] || classification=execution_blocked
  terminal_error=$2
  printf '%s %s %s\n' "${phase-P02}" "$classification" "$2"
  exit 1
}

_worker38_identity() {
  (( $# == 0 )) || block execution_blocked unexpected_argument
  [[ ${GITHUB_REPOSITORY-} == carabinshely/bandido-alcatraz-solve ]] || block execution_blocked repository
  [[ ${GITHUB_ACTOR-} == carabinshely && ${GITHUB_TRIGGERING_ACTOR-} == carabinshely ]] || block execution_blocked actor
  [[ ${WORKER38_SENDER-} == carabinshely && ${WORKER38_PR_AUTHOR-} == carabinshely ]] || block execution_blocked sender
  [[ ${GITHUB_SERVER_URL-} == https://github.com && ${GITHUB_API_URL-} == https://api.github.com ]] || block execution_blocked origin
  [[ ${RUNNER_NAME-} == bandido-alcatraz-ci ]] || block execution_blocked runner
  [[ ${GITHUB_EVENT_NAME-} == pull_request && ${WORKER38_EVENT_ACTION-} == edited && ${GITHUB_RUN_ATTEMPT-} == 1 ]] || block execution_blocked event_attempt
  [[ ${GITHUB_RUN_ID-} =~ ^[1-9][0-9]{0,17}$ && ${PR_NUMBER-} =~ ^[1-9][0-9]{0,17}$ ]] || block execution_blocked identifier
  [[ ${WORKER38_HEAD-} =~ ^[0-9a-f]{40}$ ]] || block execution_blocked head
  [[ ${WORKER38_HEAD_REF-} == research/worker38-synthetic-profile && ${WORKER38_BASE_REF-} == main ]] || block execution_blocked branch
  [[ ${WORKER38_BASE_HEAD-} == 6ff861bba828e78d8f5b75d8355f2f4a56018898 ]] || block execution_blocked base
  [[ ${WORKER38_HEAD_REPOSITORY-} == "$GITHUB_REPOSITORY" && ${WORKER38_BASE_REPOSITORY-} == "$GITHUB_REPOSITORY" ]] || block execution_blocked same_repository
  [[ ${WORKER38_BODY_CHANGED-} == true && ${WORKER38_PREVIOUS_BODY-} != *WORKER38_SYNTHETIC_ADMISSION* ]] || block execution_blocked first_marker
  [[ ${WORKER38_CURRENT_BODY-} == *WORKER38_SYNTHETIC_ADMISSION_JSON* && ${WORKER38_CURRENT_BODY-} == *END_WORKER38_SYNTHETIC_ADMISSION_JSON* && ${WORKER38_CURRENT_BODY-} == *WORKER38_SYNTHETIC_ADMISSION_SHA256* ]] || block execution_blocked missing_marker
  (( ${#WORKER38_CURRENT_BODY} <= 65536 )) || block resource_incomplete body_size
  absolute_plain_path "${RUNNER_TOOL_CACHE-}" || block execution_blocked invalid_cache
  absolute_plain_path "${GITHUB_WORKSPACE-}" || block execution_blocked invalid_source
  absolute_plain_path "${RUNNER_TEMP-}" || block execution_blocked invalid_temp
}

_worker38_clock() {
  local uptime ignored seconds fraction precision quantum=1
  IFS=' ' read -r uptime ignored < /proc/uptime || block execution_blocked clock_unavailable
  [[ $uptime =~ ^([0-9]{1,9})\.([0-9]{1,9})$ ]] || block integrity_invalid clock_shape
  seconds=${BASH_REMATCH[1]} fraction=${BASH_REMATCH[2]} precision=${#BASH_REMATCH[2]}
  fraction=${fraction}000000000
  fraction=${fraction:0:9}
  while (( precision < 9 )); do (( quantum *= 10 )); (( precision += 1 )); done
  # /proc/uptime truncates its CLOCK_BOOTTIME rendering. Charge the entire
  # unknown fractional quantum instead of ever extending a carried cutoff.
  worker38_lower_ns=$((10#$seconds * 1000000000 + 10#$fraction))
  worker38_now_ns=$((worker38_lower_ns + quantum))
}

_worker38_fixed_attempt() {
  attempt_directory=$RUNNER_TOOL_CACHE/worker38-synthetic-profile/allocations/worker38-synthetic-profile-01/run-$GITHUB_RUN_ID-attempt-1
}

_worker38_shell_terminal() {
  local result=$1
  trap - EXIT
  set +e
  [[ -n ${attempt_directory-} && -d $attempt_directory ]] || return "$result"
  printf 'schema=worker38-shell-terminal-v1\nphase=%s\nexit_status=%s\nerror=%s\nevaluator_starts=0\nscientific_classification=null\nkill_137_cause=uncertain\n' "${phase-P03}" "$result" "${terminal_error-none}" > "$attempt_directory/shell-terminal.txt"
  sync_file_and_parent "$attempt_directory/shell-terminal.txt" || return 1
  return "$result"
}

_worker38_shell() {
  _bootstrap_sanitize
  unset GH_TOKEN worker38_api_token
  exec 2>/dev/null
  phase=P03
  _worker38_identity
  for required_command in realpath readlink stat id mkdir cat sync sha256sum git timeout; do
    type -P "$required_command" >/dev/null || block execution_blocked required_command_missing
  done
  attempt_directory=
  terminal_error=none
  bootstrap_worker38_prepare
  trap 'worker38_shell_exit=$?; _worker38_shell_terminal "$worker38_shell_exit"; exit $?' EXIT
  command cat -- "$allocation_directory/reservation.txt" > "$attempt_directory/reservation.txt" || block execution_incomplete reservation_copy
  sync_file_and_parent "$attempt_directory/reservation.txt" || block execution_incomplete reservation_copy_sync
  printf 'schema=worker38-shell-prefix-v1\nphase=P03\nallocation_id=%s\nrun_id=%s\nrun_attempt=1\nreservation_file_and_directory_fsync=confirmed\nattempt_parent_fsync=confirmed\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n' "$allocation_id" "$GITHUB_RUN_ID" > "$attempt_directory/shell-prefix.txt" || block execution_incomplete prefix_write
  sync_file_and_parent "$attempt_directory/shell-prefix.txt" || block execution_incomplete prefix_sync
  _bootstrap_event_snapshot
  phase=P04
  _bootstrap_runtime
  for private_directory in "$attempt_directory/home" "$attempt_directory/tmp"; do
    command mkdir -m 0700 -- "$private_directory" || block execution_blocked private_environment_directory
    owned_private_directory "$private_directory"
  done
  : > "$attempt_directory/coordinator-output.txt" || block execution_incomplete coordinator_output_create
  sync_file_and_parent "$attempt_directory/coordinator-output.txt" || block execution_incomplete coordinator_output_sync
  command sync -- "$attempt_directory" || block execution_incomplete private_directory_sync
  _worker38_clock
  [[ ${WORKER38_STARTUP_BOOTTIME_NS-} =~ ^[1-9][0-9]{0,17}$ ]] || block integrity_invalid startup_clock
  (( worker38_now_ns - WORKER38_STARTUP_BOOTTIME_NS < 30000000000 )) || block resource_incomplete shared_shell_deadline
  printf 'version=worker38-shell-runtime-v1\nexecutable_stat=%s\nlibrary_stat=%s\nhead=%s\ntree=%s\nevent_sha256=%s\nevent_stat=%s\n' "$WORKER38_EXECUTABLE_STAT" "$WORKER38_LIBRARY_STAT" "$WORKER38_HEAD" "$WORKER38_TREE" "$WORKER38_EVENT_SHA256" "$WORKER38_EVENT_STAT" > "$attempt_directory/shell-runtime.txt" || block execution_incomplete shell_runtime_write
  sync_file_and_parent "$attempt_directory/shell-runtime.txt" || block execution_incomplete shell_runtime_sync
  # CPU is observational only; no aggregate helper CPU enforcement is claimed.
  { printf 'schema=worker38-shell-cpu-observation-v1\n'; times; } > "$attempt_directory/shell-cpu.txt"
  sync_file_and_parent "$attempt_directory/shell-cpu.txt" || block execution_incomplete shell_cpu_sync
}

_worker38_read_runtime() {
  local raw
  local -a lines
  _worker38_fixed_attempt
  [[ -f $attempt_directory/shell-runtime.txt && ! -L $attempt_directory/shell-runtime.txt ]] || block execution_blocked shell_runtime_missing
  raw=
  IFS= read -r -N 4097 raw < "$attempt_directory/shell-runtime.txt" || :
  (( ${#raw} <= 4096 )) || block resource_incomplete shell_runtime_size
  [[ $raw == *$'\n' ]] || block integrity_invalid shell_runtime_torn
  mapfile -t lines <<< "${raw%$'\n'}"
  (( ${#lines[@]} == 7 )) || block integrity_invalid shell_runtime_shape
  [[ ${lines[0]} == version=worker38-shell-runtime-v1 && ${lines[1]} =~ ^executable_stat=([0-9]+:[0-9]+:[0-9]+:[0-9]+)$ ]] || block integrity_invalid shell_runtime_shape
  WORKER38_EXECUTABLE_STAT=${lines[1]#*=}
  [[ ${lines[2]} =~ ^library_stat=([0-9]+:[0-9]+:23041360:[0-9]+)$ ]] || block integrity_invalid shell_runtime_shape
  WORKER38_LIBRARY_STAT=${lines[2]#*=}
  [[ ${lines[3]} == head="$WORKER38_HEAD" && ${lines[4]} =~ ^tree=([0-9a-f]{40})$ ]] || block integrity_invalid shell_runtime_head
  WORKER38_TREE=${lines[4]#*=}
  [[ ${lines[5]} =~ ^event_sha256=([0-9a-f]{64})$ && ${lines[6]} =~ ^event_stat=([0-9]+:[0-9]+:[0-9]+:[0-9]+)$ ]] || block integrity_invalid shell_runtime_event
  WORKER38_EVENT_SHA256=${lines[5]#*=} WORKER38_EVENT_STAT=${lines[6]#*=}
  WORKER38_EVENT_FSYNC_CONFIRMED=1
  WORKER38_EXECUTABLE=$RUNNER_TOOL_CACHE/Python/3.11.16/x64/bin/python3.11
  WORKER38_LIBRARY=$RUNNER_TOOL_CACHE/Python/3.11.16/x64/lib/libpython3.11.so.1.0
  WORKER38_RUN_ID=$GITHUB_RUN_ID WORKER38_PR_NUMBER=$PR_NUMBER
  WORKER38_BRANCH=research/worker38-synthetic-profile WORKER38_JOB=${GITHUB_JOB-measure}
  WORKER38_ALLOCATION_ID=worker38-synthetic-profile-01
  export WORKER38_EXECUTABLE WORKER38_LIBRARY WORKER38_EXECUTABLE_STAT WORKER38_LIBRARY_STAT
  export WORKER38_HEAD WORKER38_TREE WORKER38_RUN_ID WORKER38_PR_NUMBER WORKER38_BRANCH WORKER38_JOB WORKER38_ALLOCATION_ID
  export WORKER38_EVENT_SHA256 WORKER38_EVENT_STAT WORKER38_EVENT_FSYNC_CONFIRMED
}

_worker38_startup() {
  _bootstrap_sanitize
  export -n GH_TOKEN worker38_api_token
  worker38_api_token=${GH_TOKEN-}
  unset GH_TOKEN
  exec 2>/dev/null
  phase=P02
  _worker38_identity
  # The fixed shell child returns before the sole admission leaf starts.
  set +e
  command timeout --signal=KILL 30s /bin/bash --noprofile --norc -c 'source "$GITHUB_WORKSPACE/scripts/worker38-bootstrap.sh"; _worker38_shell'
  shell_exit=$?
  set -e
  if (( shell_exit != 0 )); then
    _worker38_clock
    (( worker38_now_ns - WORKER38_STARTUP_BOOTTIME_NS < 30000000000 )) || block resource_incomplete shared_shell_deadline
    block execution_blocked shared_shell_nonzero
  fi
  _worker38_read_runtime
  _worker38_clock
  [[ ${WORKER38_STARTUP_DEADLINE_BOOTTIME_NS-} =~ ^[1-9][0-9]{0,17}$ ]] || block integrity_invalid startup_deadline
  WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS=$((worker38_now_ns + 90000000000))
  if (( WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS > WORKER38_STARTUP_DEADLINE_BOOTTIME_NS )); then
    WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS=$WORKER38_STARTUP_DEADLINE_BOOTTIME_NS
  fi
  admission_seconds=$(((WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS-worker38_now_ns)/1000000000))
  (( admission_seconds > 0 && admission_seconds <= 90 )) || block resource_incomplete admission_deadline
  export WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS
  phase=P05
  set +e
  GH_TOKEN="$worker38_api_token" LD_LIBRARY_PATH="${WORKER38_LIBRARY%/*}" PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 command timeout --foreground --signal=KILL "${admission_seconds}s" "$WORKER38_EXECUTABLE" -B -s "$GITHUB_WORKSPACE/scripts/worker38/admission.py" --event "$attempt_directory/event.json" --output "$attempt_directory" --source "$GITHUB_WORKSPACE" > "$attempt_directory/admission.stdout" 2> "$attempt_directory/admission.stderr"
  admission_exit=$?
  set -e
  unset worker38_api_token GH_TOKEN
  set -o noclobber
  printf 'schema=worker38-admission-process-exit-v1\nexit_status=%s\nadmission_process_returned=true\n' "$admission_exit" > "$attempt_directory/admission-process-exit.txt" || block execution_incomplete admission_exit_observation_write
  sync_file_and_parent "$attempt_directory/admission-process-exit.txt" || block execution_incomplete admission_exit_observation_sync
  #79 is emitted only after the failed leaf confirms its immutable handoff,
  # descriptor/resource closes and timer restoration. It never admits science.
  if (( admission_exit == 79 )); then exit 79; fi
  if (( admission_exit != 0 )); then
    _worker38_clock
    (( worker38_now_ns < WORKER38_ADMISSION_DEADLINE_BOOTTIME_NS )) || block resource_incomplete admission_deadline
    block execution_blocked admission_nonzero
  fi
}

_worker38_read_admission_exit() {
  local raw read_status=0
  local -a lines
  [[ -f $attempt_directory/admission-process-exit.txt && ! -L $attempt_directory/admission-process-exit.txt ]] || block execution_blocked admission_exit_unconfirmed
  raw=
  IFS= read -r -d '' -n 513 raw < "$attempt_directory/admission-process-exit.txt" || read_status=$?
  (( read_status == 1 && ${#raw} <= 512 )) || block integrity_invalid admission_exit_shape
  [[ $raw == *$'\n' ]] || block integrity_invalid admission_exit_torn
  mapfile -t lines <<< "${raw%$'\n'}"
  (( ${#lines[@]} == 3 )) || block integrity_invalid admission_exit_shape
  [[ ${lines[0]} == schema=worker38-admission-process-exit-v1 && ${lines[1]} =~ ^exit_status=(0|[1-9][0-9]{0,2})$ && ${lines[2]} == admission_process_returned=true ]] || block integrity_invalid admission_exit_shape
  admission_exit=${lines[1]#*=}
  (( admission_exit <= 255 )) || block integrity_invalid admission_exit_status
}

_worker38_upload_readiness() {
  # Driver returns0/2 only after seal confirmation AND final timer restoration.
  # Any other process outcome cannot certify a readable leftover plan.
  (( preservation_exit == 0 || preservation_exit == 2 )) || return 1
  [[ -d $transport_directory && ! -L $transport_directory && -O $transport_directory && -r $transport_directory && -x $transport_directory && ! -w $transport_directory ]] || block execution_incomplete upload_seal_unconfirmed
  [[ -f $transport_directory/upload-plan.txt && ! -L $transport_directory/upload-plan.txt && -O $transport_directory/upload-plan.txt && -r $transport_directory/upload-plan.txt && ! -w $transport_directory/upload-plan.txt ]] || block execution_incomplete upload_seal_unconfirmed
  [[ -n ${GITHUB_OUTPUT-} ]] || block execution_incomplete upload_output_unavailable
  printf '::add-mask::%s\n' "$RUNNER_TOOL_CACHE"
  printf 'upload_ready=true\n' >> "$GITHUB_OUTPUT" || block execution_incomplete upload_output_write
}

_worker38_read_handoff() {
  local raw current_boot key index
  local -a lines expected
  expected=(version handoff_sha256 boot_id measurement_monotonic_ns measurement_boottime_ns measurement_deadline_boottime_ns attempt_path source_path head tree admission_sha256 provenance_sha256 runtime_sha256 source_map_sha256)
  [[ -f $attempt_directory/measurement-handoff.txt && ! -L $attempt_directory/measurement-handoff.txt ]] || block execution_blocked measurement_handoff_missing
  raw=
  IFS= read -r -N 4097 raw < "$attempt_directory/measurement-handoff.txt" || :
  (( ${#raw} <= 4096 )) || block resource_incomplete measurement_handoff_size
  [[ $raw == *$'\n' ]] || block integrity_invalid measurement_handoff_torn
  mapfile -t lines <<< "${raw%$'\n'}"
  (( ${#lines[@]} == ${#expected[@]} )) || block integrity_invalid measurement_handoff_shape
  for (( index=0; index<${#expected[@]}; index++ )); do
    key=${expected[index]}
    [[ ${lines[index]} == "$key="* ]] || block integrity_invalid measurement_handoff_key
    printf -v "worker38_handoff_$key" '%s' "${lines[index]#*=}"
  done
  [[ $worker38_handoff_version == worker38-handoff-v1 ]] || block integrity_invalid measurement_handoff_version
  for key in handoff_sha256 admission_sha256 provenance_sha256 runtime_sha256 source_map_sha256; do
    key=worker38_handoff_$key
    [[ ${!key} =~ ^[0-9a-f]{64}$ ]] || block integrity_invalid measurement_handoff_hash
  done
  [[ $worker38_handoff_head == "$WORKER38_HEAD" && $worker38_handoff_tree == "$WORKER38_TREE" && $worker38_handoff_attempt_path == "$attempt_directory" && $worker38_handoff_source_path == "$GITHUB_WORKSPACE" ]] || block integrity_invalid measurement_handoff_identity
  for key in measurement_monotonic_ns measurement_boottime_ns measurement_deadline_boottime_ns; do
    key=worker38_handoff_$key
    [[ ${!key} =~ ^[1-9][0-9]{0,17}$ ]] || block integrity_invalid measurement_handoff_clock
  done
  [[ $worker38_handoff_boot_id =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || block integrity_invalid measurement_handoff_boot
  IFS= read -r current_boot < /proc/sys/kernel/random/boot_id || block execution_blocked boot_unavailable
  [[ $current_boot == "$worker38_handoff_boot_id" ]] || block integrity_invalid measurement_boot_changed
  (( worker38_handoff_measurement_deadline_boottime_ns == worker38_handoff_measurement_boottime_ns + 1800000000000 )) || block integrity_invalid measurement_deadline_changed
  _worker38_clock
  (( worker38_handoff_measurement_boottime_ns <= worker38_now_ns )) || block integrity_invalid measurement_anchor_future
  measurement_seconds=$(((worker38_handoff_measurement_deadline_boottime_ns-worker38_now_ns)/1000000000))
  (( measurement_seconds > 0 && measurement_seconds <= 1800 )) || block resource_incomplete measurement_deadline
}

_worker38_science_environment() {
  local name descriptor
  # Remove every inherited export, then establish this exact positive set.
  for name in $(compgen -e); do export -n "$name"; done
  unset GH_TOKEN GITHUB_TOKEN ACTIONS_RUNTIME_TOKEN ACTIONS_ID_TOKEN_REQUEST_TOKEN worker38_api_token
  export PATH=/usr/bin:/bin LC_ALL=C
  export HOME="$attempt_directory/home" TMPDIR="$attempt_directory/tmp"
  export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 LD_LIBRARY_PATH="${WORKER38_LIBRARY%/*}"
  export GITHUB_ACTIONS=true GITHUB_EVENT_NAME=pull_request
  export RUNNER_TOOL_CACHE RUNNER_NAME GITHUB_REPOSITORY GITHUB_RUN_ID GITHUB_RUN_ATTEMPT
  export WORKER38_EXECUTABLE WORKER38_LIBRARY WORKER38_EXECUTABLE_STAT WORKER38_LIBRARY_STAT
  export WORKER38_HEAD WORKER38_TREE WORKER38_RUN_ID WORKER38_PR_NUMBER WORKER38_BRANCH WORKER38_JOB WORKER38_ALLOCATION_ID
  export WORKER38_ATTEMPT_DIRECTORY="$attempt_directory" WORKER38_SOURCE_DIRECTORY="$GITHUB_WORKSPACE"
  export WORKER38_HANDOFF_SHA256="$worker38_handoff_handoff_sha256"
  export GITHUB_OUTPUT="$attempt_directory/coordinator-output.txt"
  cd -- "$attempt_directory" || block execution_blocked science_cwd
  unset OLDPWD || block execution_blocked science_cwd
  # Bash builtin descriptor close, including inherited credential FD9. The
  # function is already parsed; the shell parser's own descriptor is not needed.
  for descriptor in /proc/self/fd/*; do
    descriptor=${descriptor##*/}
    [[ $descriptor =~ ^[0-9]+$ ]] || block integrity_invalid descriptor_shape
    if (( descriptor > 2 )); then exec {descriptor}<&- || block execution_blocked descriptor_close; fi
  done
  [[ -d /proc/self/fd && -r /proc/self/fd && -x /proc/self/fd ]] || block execution_blocked descriptor_enumeration_unavailable
  local descriptor_entries=0
  for descriptor in /proc/self/fd/*; do
    descriptor=${descriptor##*/}
    [[ $descriptor =~ ^[0-9]+$ ]] || block integrity_invalid descriptor_shape
    (( descriptor_entries += 1 ))
    # Globbing can observe its own directory descriptor, closed before this
    # body runs. Reject a surviving entry, not a stale expanded pathname.
    if (( descriptor > 2 )) && [[ -e /proc/self/fd/$descriptor || -L /proc/self/fd/$descriptor ]]; then
      block execution_blocked descriptor_close_unconfirmed
    fi
  done
  (( descriptor_entries > 0 )) || block execution_blocked descriptor_enumeration_unavailable
}

_worker38_preserve() {
  local raw current_boot preservation_monotonic_ms preservation_boottime_ms preservation_boot_id preservation_seconds
  local -a lines
  phase=PRESERVE
  [[ -f $attempt_directory/coordinator-output.txt && ! -L $attempt_directory/coordinator-output.txt ]] || block execution_blocked preservation_handoff_missing
  raw=
  IFS= read -r -N 1025 raw < "$attempt_directory/coordinator-output.txt" || :
  (( ${#raw} <= 1024 )) || block resource_incomplete preservation_handoff_size
  [[ $raw == *$'\n' ]] || block execution_blocked preservation_handoff_unconfirmed
  mapfile -t lines <<< "${raw%$'\n'}"
  (( ${#lines[@]} == 3 )) || block integrity_invalid preservation_handoff_shape
  [[ ${lines[0]} =~ ^preservation_deadline_monotonic_ms=([1-9][0-9]{0,14})$ ]] || block integrity_invalid preservation_monotonic_shape
  preservation_monotonic_ms=${lines[0]#*=}
  [[ ${lines[1]} =~ ^preservation_deadline_boottime_ms=([1-9][0-9]{0,14})$ ]] || block integrity_invalid preservation_boottime_shape
  preservation_boottime_ms=${lines[1]#*=}
  [[ ${lines[2]} =~ ^preservation_boot_id=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$ ]] || block integrity_invalid preservation_boot_shape
  preservation_boot_id=${lines[2]#*=}
  IFS= read -r current_boot < /proc/sys/kernel/random/boot_id || block execution_blocked preservation_boot_unavailable
  [[ $current_boot == "$preservation_boot_id" && $preservation_boot_id == "$worker38_handoff_boot_id" ]] || block integrity_invalid preservation_boot_changed
  _worker38_clock
  preservation_seconds=$(((preservation_boottime_ms*1000000-worker38_now_ns)/1000000000))
  (( preservation_seconds > 0 && preservation_seconds <= 600 )) || block resource_incomplete preservation_original_deadline
  allocation_directory=${attempt_directory%/*}
  transport_directory=$allocation_directory/transport-$GITHUB_RUN_ID-attempt-1
  # Optional bulk work runs only under the original remaining preservation bound.
  set +e
  (
    _worker38_science_environment
    _worker38_clock
    preservation_seconds=$(((preservation_boottime_ms*1000000-worker38_now_ns)/1000000000))
    (( preservation_seconds > 0 && preservation_seconds <= 600 )) || block resource_incomplete preservation_original_deadline
    exec /usr/bin/timeout --foreground --signal=KILL "${preservation_seconds}s" "$WORKER38_EXECUTABLE" -B -s "$WORKER38_SOURCE_DIRECTORY/scripts/run_worker38_synthetic.py" preserve --attempt "$attempt_directory" --destination "$transport_directory" --report "$allocation_directory/verification-$GITHUB_RUN_ID.json" --recovery-report "$allocation_directory/recovery-$GITHUB_RUN_ID.json" --admission "$attempt_directory/admission-inputs/admission.json" --admission-sha256 "$worker38_handoff_admission_sha256" --admission-provenance "$attempt_directory/admission-inputs/provenance.json" --admission-provenance-sha256 "$worker38_handoff_provenance_sha256" --expected-head "$WORKER38_HEAD" --expected-tree "$WORKER38_TREE" --expected-workflow-run "$GITHUB_RUN_ID" --preservation-deadline-monotonic-ms "$preservation_monotonic_ms" --admission-exit-status "$admission_exit" --coordinator-exit-status "$measurement_exit" < /dev/null > "$allocation_directory/preservation-$GITHUB_RUN_ID.stdout" 2> "$allocation_directory/preservation-$GITHUB_RUN_ID.stderr"
  )
  preservation_exit=$?
  set -e
  _worker38_upload_readiness || return "$preservation_exit"
  return "$preservation_exit"
}

_worker38_preserve_startup_failure() {
  local raw read_status=0 current_boot preservation_monotonic_ms preservation_boottime_ms preservation_boot_id preservation_seconds startup_failure_handoff_sha256
  local -a lines
  phase=STARTUP_PRESERVE
  _worker38_read_runtime
  _worker38_read_admission_exit
  (( admission_exit == 79 )) || block execution_blocked startup_failure_exit_unconfirmed
  [[ -f $attempt_directory/startup-preservation-handoff.txt && ! -L $attempt_directory/startup-preservation-handoff.txt ]] || block execution_blocked startup_failure_handoff_missing
  raw=
  IFS= read -r -d '' -n 1025 raw < "$attempt_directory/startup-preservation-handoff.txt" || read_status=$?
  (( read_status == 1 && ${#raw} <= 1024 )) || block integrity_invalid startup_failure_handoff_shape
  [[ $raw == *$'\n' ]] || block integrity_invalid startup_failure_handoff_torn
  mapfile -t lines <<< "${raw%$'\n'}"
  (( ${#lines[@]} == 5 )) || block integrity_invalid startup_failure_handoff_shape
  [[ ${lines[0]} == version=worker38-startup-failure-v1 && ${lines[1]} =~ ^startup_failure_handoff_sha256=([0-9a-f]{64})$ ]] || block integrity_invalid startup_failure_handoff_identity
  startup_failure_handoff_sha256=${lines[1]#*=}
  [[ ${lines[2]} =~ ^preservation_deadline_monotonic_ms=([1-9][0-9]{0,14})$ ]] || block integrity_invalid startup_failure_monotonic_shape
  preservation_monotonic_ms=${lines[2]#*=}
  [[ ${lines[3]} =~ ^preservation_deadline_boottime_ms=([1-9][0-9]{0,14})$ ]] || block integrity_invalid startup_failure_boottime_shape
  preservation_boottime_ms=${lines[3]#*=}
  [[ ${lines[4]} =~ ^preservation_boot_id=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$ ]] || block integrity_invalid startup_failure_boot_shape
  preservation_boot_id=${lines[4]#*=}
  IFS= read -r current_boot < /proc/sys/kernel/random/boot_id || block execution_blocked startup_failure_boot_unavailable
  [[ $current_boot == "$preservation_boot_id" ]] || block integrity_invalid startup_failure_boot_changed
  _worker38_clock
  preservation_seconds=$(((preservation_boottime_ms*1000000-worker38_now_ns)/1000000000))
  (( preservation_seconds > 0 && preservation_seconds <= 600 )) || block resource_incomplete startup_failure_original_deadline
  allocation_directory=${attempt_directory%/*}
  transport_directory=$allocation_directory/transport-$GITHUB_RUN_ID-attempt-1
  worker38_handoff_handoff_sha256=$startup_failure_handoff_sha256
  worker38_handoff_boot_id=$preservation_boot_id
  set +e
  (
    _worker38_science_environment
    _worker38_clock
    preservation_seconds=$(((preservation_boottime_ms*1000000-worker38_now_ns)/1000000000))
    (( preservation_seconds > 0 && preservation_seconds <= 600 )) || block resource_incomplete startup_failure_original_deadline
    exec /usr/bin/timeout --foreground --signal=KILL "${preservation_seconds}s" "$WORKER38_EXECUTABLE" -B -s "$WORKER38_SOURCE_DIRECTORY/scripts/run_worker38_synthetic.py" preserve --attempt "$attempt_directory" --destination "$transport_directory" --report "$allocation_directory/verification-$GITHUB_RUN_ID.json" --recovery-report "$allocation_directory/recovery-$GITHUB_RUN_ID.json" --startup-failure-handoff-sha256 "$startup_failure_handoff_sha256" --expected-head "$WORKER38_HEAD" --expected-tree "$WORKER38_TREE" --expected-workflow-run "$GITHUB_RUN_ID" --preservation-deadline-monotonic-ms "$preservation_monotonic_ms" --admission-exit-status "$admission_exit" --coordinator-exit-status not_started < /dev/null > "$allocation_directory/preservation-$GITHUB_RUN_ID.stdout" 2> "$allocation_directory/preservation-$GITHUB_RUN_ID.stderr"
  )
  preservation_exit=$?
  set -e
  _worker38_upload_readiness || return "$preservation_exit"
  # Sealed zero-entry failure remains failed even if preservation succeeded.
  return 1
}

_worker38_main() {
  (( $# == 0 )) || block execution_blocked unexpected_argument
  _bootstrap_sanitize
  export -n GH_TOKEN worker38_api_token
  worker38_api_token=${GH_TOKEN-}
  unset GH_TOKEN
  exec 2>/dev/null
  phase=P02
  _worker38_identity
  _worker38_clock
  WORKER38_STARTUP_BOOTTIME_NS=$worker38_lower_ns
  WORKER38_STARTUP_DEADLINE_BOOTTIME_NS=$((worker38_lower_ns+120000000000))
  export WORKER38_STARTUP_BOOTTIME_NS WORKER38_STARTUP_DEADLINE_BOOTTIME_NS
  type -P timeout >/dev/null || block execution_blocked required_command_missing
  set +e
  GH_TOKEN="$worker38_api_token" command timeout --signal=KILL 120s /bin/bash --noprofile --norc -c 'source "$GITHUB_WORKSPACE/scripts/worker38-bootstrap.sh"; _worker38_startup'
  startup_exit=$?
  set -e
  unset worker38_api_token GH_TOKEN
  if (( startup_exit == 79 )); then
    _worker38_preserve_startup_failure
    return 1
  fi
  if (( startup_exit != 0 )); then
    _worker38_clock
    (( worker38_now_ns < WORKER38_STARTUP_DEADLINE_BOOTTIME_NS )) || block resource_incomplete startup_deadline
    block execution_blocked startup_nonzero
  fi
  # The120s timeout has returned. Only builtins run before the measurement
  # timeout is installed from the immutable carried deadline.
  _worker38_read_runtime
  _worker38_read_admission_exit
  (( admission_exit == 0 )) || block execution_blocked admission_exit_nonzero
  _worker38_read_handoff
  phase=MEASURE
  set +e
  (
    _worker38_science_environment
    _worker38_clock
    measurement_seconds=$(((worker38_handoff_measurement_deadline_boottime_ns-worker38_now_ns)/1000000000))
    (( measurement_seconds > 0 && measurement_seconds <= 1800 )) || block resource_incomplete measurement_deadline
    exec /usr/bin/timeout --foreground --signal=USR1 --kill-after=600s "${measurement_seconds}s" "$WORKER38_EXECUTABLE" -B -s "$WORKER38_SOURCE_DIRECTORY/scripts/run_worker38_synthetic.py" measure --attempt "$attempt_directory" --admission "$attempt_directory/admission-inputs/admission.json" --admission-sha256 "$worker38_handoff_admission_sha256" --admission-provenance "$attempt_directory/admission-inputs/provenance.json" --admission-provenance-sha256 "$worker38_handoff_provenance_sha256" < /dev/null > "$attempt_directory/measure.stdout" 2> "$attempt_directory/measure.stderr"
  )
  measurement_exit=$?
  set -e
  # A missing original preservation anchor cannot be replaced here.
  _worker38_preserve
  return "$measurement_exit"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  _worker38_main "$@"
fi
