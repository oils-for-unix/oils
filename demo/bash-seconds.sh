#!/usr/bin/env bash
#
# Demo of $SECONDS

seconds=${1:-1}
sleep $seconds
echo "Task took $SECONDS seconds to complete."
