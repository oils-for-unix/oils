# Benchmarking stub that's run with various shells, including dash

set -e

readonly PY27_DIR=$PWD/Python-2.7.13

sh_path=$1
files_out_dir=$2

# We leave output files in the dir that the harness will save.
#
# GNU autoconf supports running configure from a different directory.

cd $files_out_dir

"$sh_path" $PY27_DIR/configure
