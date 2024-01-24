#!/usr/bin/env bash
#


long-running-task() {
    sleep 10
}

long-running-task
echo "Task took $SECONDS seconds to complete."

