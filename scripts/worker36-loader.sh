#!/usr/bin/env bash
# Source-only Worker36 launcher foundation; this file never starts Python.
# Zero arguments observe the actual corresponding library for preflight.
# Two arguments verify an explicitly supplied library SHA256 and byte size.
worker36_loader_setup() {
  local name tool_cache executable expected_executable library directory
  local executable_sha library_sha library_size before after expected_sha expected_size
  if [[ "$#" != 0 && "$#" != 2 ]]; then
    printf '%s\n' 'worker36 loader: expected zero arguments or explicit library SHA256 and size' >&2
    return 1
  fi
  expected_sha=${1-}
  expected_size=${2-}
  if [[ "$#" == 2 ]] && { [[ ! "$expected_sha" =~ ^[0-9a-f]{64}$ ]] ||
                           [[ ! "$expected_size" =~ ^[1-9][0-9]*$ ]]; }; then
    printf '%s\n' 'worker36 loader: invalid explicit library pin' >&2
    return 1
  fi
  # Shell builtins sanitize every inherited loader/Python name before external
  # path, stat or hash probes. Ambient directories are never consulted.
  while IFS= read -r name; do
    if [[ "$name" == LD* || "$name" == PYTHON* ]]; then
      unset "$name" || return 1
    fi
  done < <(compgen -v)
  unset WORKER36_PYTHON WORKER36_LOADER_DIRECTORY WORKER36_LOADER_LIBRARY \
    WORKER36_LOADER_SHA256 WORKER36_LOADER_SIZE_BYTES || return 1
  tool_cache=${RUNNER_TOOL_CACHE-}
  if [[ "$tool_cache" != /* || "$tool_cache" == *:* || "$tool_cache" == *$'\n'* ||
        "$tool_cache" == *$'\r'* || ! -d "$tool_cache" || -L "$tool_cache" ]]; then
    printf '%s\n' 'worker36 loader: canonical trusted RUNNER_TOOL_CACHE required' >&2
    return 1
  fi
  [[ "$(readlink -f -- "$tool_cache")" == "$tool_cache" ]] || return 1
  expected_executable="$tool_cache/Python/3.11.16/x64/bin/python3.11"
  executable=$(command -v python) || return 1
  [[ "$executable" == /* ]] || return 1
  executable=$(readlink -f -- "$executable") || return 1
  [[ "$executable" == "$expected_executable" && -f "$executable" &&
     ! -L "$executable" && -x "$executable" ]] || return 1
  before=$(stat -Lc '%d:%i:%s:%y:%z:%f' -- "$executable") || return 1
  executable_sha=$(sha256sum -- "$executable") || return 1
  executable_sha=${executable_sha%% *}
  after=$(stat -Lc '%d:%i:%s:%y:%z:%f' -- "$executable") || return 1
  [[ "$before" == "$after" && "$executable_sha" == \
     a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc ]] || return 1
  directory="${executable%/bin/python3.11}/lib"
  library="$directory/libpython3.11.so.1.0"
  [[ "$library" == "$tool_cache/Python/3.11.16/x64/lib/libpython3.11.so.1.0" &&
     -d "$directory" && ! -L "$directory" && -f "$library" && ! -L "$library" ]] || return 1
  [[ "$(readlink -f -- "$directory")" == "$directory" &&
     "$(readlink -f -- "$library")" == "$library" ]] || return 1
  before=$(stat -Lc '%d:%i:%s:%y:%z:%f' -- "$library") || return 1
  library_sha=$(sha256sum -- "$library") || return 1
  library_sha=${library_sha%% *}
  library_size=$(stat -Lc '%s' -- "$library") || return 1
  after=$(stat -Lc '%d:%i:%s:%y:%z:%f' -- "$library") || return 1
  [[ "$before" == "$after" && "$library_sha" =~ ^[0-9a-f]{64}$ &&
     "$library_size" =~ ^[1-9][0-9]*$ && ! -L "$library" ]] || return 1
  if [[ "$#" == 2 ]]; then
    [[ "$library_sha" == "$expected_sha" && "$library_size" == "$expected_size" ]] || return 1
  fi
  export WORKER36_PYTHON="$executable"
  export WORKER36_LOADER_DIRECTORY="$directory" WORKER36_LOADER_LIBRARY="$library"
  export WORKER36_LOADER_SHA256="$library_sha" WORKER36_LOADER_SIZE_BYTES="$library_size"
  export LD_LIBRARY_PATH="$directory" PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
}
