#!/bin/sh

MYPYPATH=$1    # e.g. $REPO_ROOT/mycpp
preamble_path=$2
out=$3
shift 3

# Add an extra flag, and also depends on _bin/datalog
exec _bin/shwrap/mycpp_main $MYPYPATH $preamble_path $out --minimize-stack-roots "$@"
