#!/bin/bash
#
# Nice examples from blog post feedback.
#
# Usage:
#   ./hard-coded-descriptors.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://lobste.rs/s/bqftd6/avoid_directly_manipulating_file
#
# - "One thing that I have found non-{0,1,2} FDs useful for however is when
#   tools (e.g. gpg) take a --passphrase-fd argument, useful for when you are
#   also redirecting some other thing into stdin."
# - "Some protocols (like djb’s checkpassword or doit) rely on specific file
#   descriptors"

# https://www.reddit.com/r/bash/comments/6td8j2/avoid_directly_manipulating_file_descriptors_in/

interactive-stdin() {
  local path=$0  # This script
	while read line <&"$fd" ; do
    echo "[$line]"
    read -p "Continue? " ans 
    [[ "$ans" != yes ]] && exit 1
	done {fd}< $path
}

# https://www.reddit.com/r/oilshell/comments/6tch5v/avoid_directly_manipulating_file_descriptors_in/

log-dates() {
  exec {fd}> >(while IFS= read -r line; do printf "[%s] %s\n" "$(date)" "$line"; done)
  echo "Hello" >&"$fd"
  echo "Goodbye" >&"$fd"
}

tee-like() {
  local log=_tmp/tee-like.txt

  >$log  # truncate

  exec {fd}> >(while IFS= read -r line; do printf "%s\n" "$line"; printf "%s\n" "$line" >&3; done 3>>"$log")
  echo "Hello" >&"$fd"
  echo "Goodbye" >&"$fd"

  echo
  echo "Contents of $log:"
  cat $log
}

pipe-stderr() {
  local log=_tmp/pipe-stderr.log
  set +o errexit

  ls -l /etc/passwd not_a_file 3>&1 1>&2 2>&3 \
    | awk '{print "ERROR:" $0}' >$log

  # Another idiom, this seems wrong because of 3>&-
  exec 3>&1
  ls -l /etc/passwd 'not_a_file_2' 2>&1 >&3 3>&- \
    | awk '{print "ERROR:" $0}' >>$log
  exec 3>&-

  echo
  echo "Contents of $log:"
  cat $log
}

_zip() {
  ( # use a subshell to ensure the FD changes don't affect the caller
  exec 4<"$1" 5<"$2"
  while IFS="" read -u 4 a && read -u 5 b; do
    printf "%s %s\n" "$a" "$b"
  done
  )
}

zip-demo() {
  seq 1 5 > _tmp/left.txt
  seq 5 10 > _tmp/right.txt
  _zip _tmp/{left,right}.txt 
}


_work() {
  local id=$1
  echo "Job $id"
  for i in 1 2 3; do
    echo "... $i ..."
    sleep 0.2
  done
}

# man flock
_flock() {
  (
    flock -n 9 || {
      echo "Another job is already running; aborting"
      exit 1
    }
    "$@"

  ) 9>_tmp/mylockfile
}

flock-demo() {
  _work A
  _work B

  # Instead of running
  $0 _flock _work C &
  $0 _flock _work D &  # One is already running
  wait
  wait
}


"$@"
