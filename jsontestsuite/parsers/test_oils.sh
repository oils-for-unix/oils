#!/usr/bin/env ysh

REPO_ROOT=$(cd $(dirname $0)/../..; pwd)

$REPO_ROOT/_bin/cxx-opt/osh -c 'json read' < "$1"

