#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
#
# Start CollabTrans backend with crash reporting.
# When the backend exits abnormally (e.g. OOM Killed), appends diagnostic info
# to logs/crash_report.log. The script itself is lightweight and won't be killed.
#
# Usage: ./run_backend.sh [options]
# With no arguments, defaults to: -i -p 8020
# Example: ./run_backend.sh  (same as -i -p 8020)
# Example: ./run_backend.sh -i -p 8081

set -u

# Project root = directory containing this script (and the collabtrans package / logs)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="${COLLABTRANS_ROOT:-$SCRIPT_DIR}"
LOGDIR="${REPO_ROOT}/logs"
CRASH_LOG="${LOGDIR}/crash_report.log"
APP_LOG="${LOGDIR}/app.log"
DMESG_TAIL=60
APP_LOG_TAIL=200

mkdir -p "$LOGDIR"

# Default args when none given: -i -p 8020
if [ $# -eq 0 ]; then
    set -- -i -p 8020
fi

run_backend() {
    cd "$REPO_ROOT" && exec python -m collabtrans.cli "$@"
}

# Run backend in foreground; capture exit code when it exits (including when killed)
run_backend "$@"
EXIT=$?

if [ "$EXIT" -ne 0 ]; then
    TIMESTAMP="$(date -Iseconds 2>/dev/null || date '+%Y-%m-%d %H:%M:%S')"
    {
        echo ""
        echo "========== Crash report =========="
        echo "Time:     $TIMESTAMP"
        echo "Exit:     $EXIT"
        if [ "$EXIT" -eq 137 ]; then
            echo "Signal:   SIGKILL (9) – often OOM killer"
        elif [ "$EXIT" -eq 143 ]; then
            echo "Signal:   SIGTERM (15)"
        elif [ "$EXIT" -ge 128 ]; then
            SIG=$((EXIT - 128))
            echo "Signal:   $SIG"
        fi
        echo "Cwd:      $REPO_ROOT"
        echo ""

        if [ "$EXIT" -eq 137 ] || [ "$EXIT" -eq 143 ]; then
            echo "--- Kernel messages (dmesg, last ${DMESG_TAIL}) ---"
            (dmesg -T 2>/dev/null || dmesg 2>/dev/null) | tail -n "$DMESG_TAIL" || true
            echo ""
            echo "--- Memory (free -m) ---"
            free -m 2>/dev/null || true
            echo ""
        fi

        echo "--- Last ${APP_LOG_TAIL} lines of app.log ---"
        if [ -f "$APP_LOG" ]; then
            tail -n "$APP_LOG_TAIL" "$APP_LOG" || true
        else
            echo "(app.log not found)"
        fi
        echo "========== End of crash report =========="
    } >> "$CRASH_LOG" 2>/dev/null

    echo "Backend exited with code $EXIT. Diagnostic info appended to: $CRASH_LOG" >&2
fi

exit "$EXIT"
