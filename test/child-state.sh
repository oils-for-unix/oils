#!/usr/bin/env bash
#
# Usage:
#   ./child-state.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

self-fd() {
  ### C program that prints its own file descriptor state
  #
  #   Similar to ls -l, but it doesn't require another process.

  cat << 'EOF'
#include <errno.h>
#include <dirent.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>

int main() {
    printf("pid %d\n", getpid());

    errno = 0;
    off_t pos = lseek(100, 0, SEEK_CUR);
    if (pos == -1) {
        printf("lseek: FD 100 is NOT open (errno: %d)\n", errno);
    } else {
        printf("lseek: FD 100 IS open (position: %ld)\n", pos);
    }

    DIR *d = opendir("/proc/self/fd");
    struct dirent *e;
    char path[256], target[256];

    while ((e = readdir(d))) {
        if (e->d_name[0] == '.') continue;

        snprintf(path, sizeof(path), "/proc/self/fd/%s", e->d_name);
        ssize_t len = readlink(path, target, sizeof(target) - 1);

        if (len != -1) {
            target[len] = '\0';
            printf("%s -> %s\n", e->d_name, target);
        }
    }

    closedir(d);
    return 0;
}
EOF
}

compare-shells() {
  local osh_cpp=_bin/cxx-dbg/osh
  ninja $osh_cpp

  self-fd > _tmp/self-fd.c
  gcc -o _tmp/self-fd _tmp/self-fd.c
  chmod +x _tmp/self-fd

  local -a shells=(bash dash mksh zsh bin/osh $osh_cpp)

  for sh in ${shells[@]}; do
    echo
    echo "---- $sh ----"
    echo

    # Hm I'm not seeing descriptor 100 open here?

    #$sh -c '_tmp/self-fd >/dev/null 1>&2; echo done'
    $sh -c 'echo "shell pid $$"; _tmp/self-fd; echo done'
  done
}

"$@"
