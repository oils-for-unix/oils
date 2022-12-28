# Benchmarking stub that's run with various shells, including dash

set -e

readonly PY27_DIR=$PWD/Python-2.7.13

main() {
  local sh_path=$1
  local files_out_dir=$2

  local sh_run_path
  case $sh_path in
    /*)  # Already absolute
      sh_run_path=$sh_path
      ;;
    */*)  # It's relative, so make it absolute
      sh_run_path=$PWD/$sh_path
      ;;
    *)  # 'dash' should remain 'dash'
      sh_run_path=$sh_path
      ;;
  esac

  # We leave output files in the dir that the harness will save.
  #
  # GNU autoconf supports running configure from a different directory.

  cd $files_out_dir

  "$sh_run_path" $PY27_DIR/configure
}

main "$@"
