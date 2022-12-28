# Benchmarking stub that's run with various shells, including dash

set -e

main() {
  local sh_path=$1
  local files_out_dir=$2
  local conf_dir=$3

  local sh_abs_path=$PWD/$sh_path

  cd $conf_dir

  touch __TIMESTAMP

  "$sh_abs_path" ./configure

  # This extra step is added to the resource usage of ./configure, but it's OK
  # for now

  echo "COPYING to $files_out_dir"
  find . -type f -newer __TIMESTAMP \
    | xargs -I {} -- cp --verbose {} $files_out_dir
}

main "$@"
