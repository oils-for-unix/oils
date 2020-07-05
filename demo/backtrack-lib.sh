#
# Portable Library
#

readonly GLOB_TMP=_tmp/glob-backtrack

repeat() {
  local s=$1
  local n=$2

  for i in $(seq $n); do
    echo -n "$s"
  done
}

glob_bench() {
  local max=${1:-5}
  cd $GLOB_TMP

  for i in $(seq $max); do
    local pat="$(repeat 'a*' $i)b"
    time echo $pat
    echo
  done
}

fnmatch_task() {
  local text=$1
  local pat=$2

  case $text in
    ($pat)
      echo yes
      ;;
    (*)
      echo no
      ;;
  esac
}

fnmatch_bench() {
  local max=${1:-5}
  cd $GLOB_TMP

  local text=$(repeat a 100)
  for i in $(seq $max); do
    local pat="$(repeat 'a*' $i)b"
    time fnmatch_task "$text" "$pat"

    echo
  done
}


