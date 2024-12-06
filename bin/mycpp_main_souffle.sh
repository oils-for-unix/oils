#!/bin/sh

MYPYPATH=$1    # e.g. $REPO_ROOT/mycpp
out=$2
shift 2

# Add an extra flag, and also depends on _bin/datalog
exec _bin/shwrap/mycpp_main $MYPYPATH $out --minimize-stack-roots "$@"
