#!bin/osh
#
# Usage:
#  demo/noclobber-race.sh setup-adversary-fast
#  demo/noclobber-race.sh demo bin/osh
#  demo/noclobber-race.sh demo _bin/cxx-opt/osh   # Will take longer, but will eventually get a race
#                                                 # Always under ~150 times on my machine.
#  demo/noclobber-race.sh demo bash               # Should never exit having found a race

## Create a special file _tmp/special so that echo a >_tmp/special is VALID under noclobber
create-special() {
  #echo normal
  ln -sf /dev/null _tmp/special
  #echo special
}

## Create a normal file _tmp/special so that echo a >_tmp/special is INVALID under noclobber
create-normal() {
  #echo special
  ln -sf $PWD/_tmp/protectme _tmp/special
  #echo normal
}

## Try to write to _tmp/special without clobbering
noclobber-process() {
  set -C  # enable noclobber
  echo howdy > _tmp/special
}

## Try to break the noclobber
adversary() {
  # Cycle _tmp/special between a symlink to /dev/null and a normal file really fast
  #for _ in {0..1000}; do
  while true; do
    create-special
    #sleep 0.1
    create-normal
    #sleep 0.1
  done

  echo adversary dead
}

## Create a faster version of the adversary function, but in C
setup-adversary-fast() {
  cat >_tmp/adversary.c <<EOF
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(x)       \
  do {                 \
    if (x) exit(1);    \
  } while (0)

int main(int argc, const char** argv) {
  if (argc != 3) {
    fprintf(stderr, "Usage: %s <path-special> <path-protectme>\n", argv[0]);
    return 2;
  }

  const char* pathSpecial = argv[1];
  const char* pathProtectMe = argv[2];

  while (1) {
    // Note: we symlink into a temporary and then rename as otherwise
    // symlink(2) will fail with EEXIST.

    // create-special
    CHECK(symlink("/dev/null", "intermediate"));
    CHECK(rename("intermediate", pathSpecial));

    // create-normal
    CHECK(symlink(pathProtectMe, "intermediate"));
    CHECK(rename("intermediate", pathSpecial));
  }

  return 0;
}

EOF

  cc _tmp/adversary.c -o _tmp/adversary
}

## Sometimes ^C will stop the _temp/adversary program in a state where we have
## leftover files. This removes them.
cleanup() {
  rm -f intermediate
}

## Run the faster version of `adversary`
adversary-fast() {
  cleanup
  _tmp/adversary _tmp/special "$PWD/_tmp/protectme"
}

## The actual demo
demo() {
  if [[ $# != 1 ]]; then
    echo "Usage: $0 demo <shell>" >&2
    return 2
  fi
  local SH=$1

  echo secret > _tmp/protectme

  #adversary & -- Too slow!
  adversary-fast &
  local adversary_pid=$!

  tries=0
  while diff <(echo secret) _tmp/protectme; do
    printf .
    tries=$(($tries + 1))
    $SH "$0" noclobber-process 2>/dev/null
  done
  echo
  echo 'got it!'

  kill -9 "$adversary_pid"
  wait
  cleanup

  echo "Took $tries tries"
}

"$@"
