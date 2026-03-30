#!/bin/bash

SCRIPT_PATH="$(realpath "${0}")"
SCRIPT_DIR="$(dirname "${SCRIPT_PATH}")"

export UBSAN_OPTIONS=halt_on_error=false
export ASAN_OPTIONS=halt_on_error=false:detect_leaks=0
"${SCRIPT_DIR}/sat" "$1" &
PID=$!

handler() {
    kill -s SIGTERM $PID
}

trap handler SIGINT
trap handler SIGTERM

# trap resumes execution after the command during which it was
# triggered so we need to wait in a loop to see if we can wait on the
# sat solver and then wait on it...
while kill -0 $PID > /dev/null 2>&1
do
    wait $PID
done
