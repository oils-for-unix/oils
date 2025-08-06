#!/usr/bin/env bash
#
# Usage:
#   ./aports-debug.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

chroot-manifest() {
  local name=${1:-foo}

  # TODO: use this to help plan OCI layers
  # 251,904 files after a build of mpfr

  local out=_tmp/$name.manifest.txt

  # pipefail may fail
  set +o errexit
  sudo find $CHROOT_DIR \
    -name proc -a -prune -o \
    -type f -a -printf '%P %s\n' |
    sort | tee $out

  echo
  echo "Wrote $out"
}

show-chroot() {
  sudo tree $CHROOT_HOME_DIR/oils/_tmp
}

sizes() {
  set +o errexit

  # 312 MB
  sudo du --si -s $CHROOT_DIR 

  # 29 MB after 80 source packages, that's not so much

  # getting up to 373 M though - worth sharding
  sudo du --si -s $CHROOT_DIR/var/cache

  sudo du --si -s $CHROOT_DIR/var/cache/distfiles

  # 110 MB just of logs
  # need to thin these out
  sudo du --si -s $CHROOT_HOME_DIR/oils/_tmp/

  sudo du --si -s $BASE_DIR/
}

archived-fetched() {
  local tar=_chroot/distfiles.tar
  tar --create --file $tar --directory $CHROOT_DIR/var/cache/distfiles .

  tar --list < $tar
  echo
  ls -l --si $tar
  echo
}

filter-basename() {
  sed 's|.*/||g'
}

readonly C_BUG='cannot create executable|cannot compile programs|No working C compiler'
readonly B_BUG='builddeps failed'

grep-c-bug-2() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-05-baseline}

  egrep "$C_BUG" $epoch_dir/*/baseline/log/* #| filter-basename 
}

grep-b-bug-2() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-05-baseline}

  egrep "$B_BUG" $epoch_dir/*/baseline/log/* #| filter-basename 
}

grep-c-bug() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-04-rootbld}

  egrep -l "$C_BUG" $epoch_dir/*/baseline/log/* | filter-basename > _tmp/b.txt
  egrep -l "$C_BUG" $epoch_dir/*/osh-as-sh/log/* | filter-basename > _tmp/o.txt

  wc -l _tmp/{b,o}.txt
  diff -u _tmp/{b,o}.txt || true
  echo
  echo done
}

grep-b-bug() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-04-rootbld}

  egrep "$B_BUG" $epoch_dir/*/baseline/log/* 

  egrep -l "$B_BUG" $epoch_dir/*/baseline/log/* | filter-basename > _tmp/b-b.txt
  egrep -l "$B_BUG" $epoch_dir/*/osh-as-sh/log/* | filter-basename > _tmp/b-o.txt

  wc -l _tmp/b-{b,o}.txt
  diff -u _tmp/b-{b,o}.txt || true
  echo
  echo done
}

update-build-server() {
  ssh -A he.oils.pub 'set -x; cd git/oils-for-unix/oils; git fetch; git status'
}

bwrap-demo() {
  # chroot only
  user-chroot sh -c '
  whoami; pwd; ls -l /
  set -x
  cat /proc/sys/kernel/unprivileged_userns_clone
  cat /proc/sys/user/max_user_namespaces
  unshare --user echo "Namespaces work"
  '

  user-chroot sh -c 'bwrap ls -l /'
}

bwrap-debian-demo() {
  bwrap \
    --bind $CHROOT_DIR / \
    --proc /proc \
    --bind /proc/sys/kernel/overflowuid /proc/sys/kernel/overflowuid \
    --bind /proc/sys/kernel/overflowgid /proc/sys/kernel/overflowgid \
    --dev /dev \
    -- \
    sh 
      #-c 'ls /; bwrap --proc /proc --dev /dev -- sh -c "nested bwrap"'
}

login-shell-demo() {
  # shopt -p login_shell is a bash extension
  # so is exec -a
  local sh=${1:-bash}

  local detect='echo dollar0=$0; shopt -p login_shell; true'

  echo EXEC
  ( exec -- $sh -c "$detect" )
  # invoke with different argv[0]
  ( exec -a "-$sh" -- $sh -c "$detect" )
  echo

  echo 'sh -l'
  $sh -c "$detect"
  # Hm it doesn't set dollar0 to -, but it still turns on the login shell.
  # Gah.
  $sh -l -c "$detect"
  echo

  echo 'sudo'
  sudo -- $sh -c "$detect"
  sudo --login $sh -c "$detect"  # wait it's not set here?
  echo

  return

  # requires entering password - requires root

  echo 'su'
  su andy $sh -c "$detect"
  su -l andy $sh -c "$detect"  # wait it's not set here?
  echo

  # Conclusion:
  #
  # There are FOUR ways to set a login shell
  #
  # - exec -a "-$sh" -- $sh
  #   - this is a bash builtin, so external tools can't invoke it
  #   - exec -a is also not POSIX; it's a bash thing
  # - sudo --login (aka sudo -i, which is confusing!)
  # - su -l
  #   - requires  password?
  # - bash -l
  #   - not POSIX
  #
  # TODO: bubblewrap should have control over argv[0]?
  # We can also use the symlink trick: create /bin/-bash next to /bin/bash!

  # Debian also has: https://wiki.debian.org/Schroot
}

# CONJECTURE: login shell is for ONE TIME initialization of state that's INHERITED
# - umask is inherited
# - env vars are inherited
#
# Claude AI has a good argument against it:
# - PS1 is not inherited
# - shopt -s histappend is not inherited
#
# Examples of login shells
# - ssh
# - sudo -i and su -l
# - but NOT tmux?

# Good chat:
# https://claude.ai/share/497778f4-fd11-4daf-9be6-9fe195e19df9
#
# "So then for /etc/profile for login shells, isn't it true that you should
# ONLY add inherited state like $PATH and $LANG and umask?       And then
# everything else should be initialized every time you start a new shell,
# whether it's login or not, like shopt -s histappend"
#
# Violating this principle causes:
#
# Problem 1: Missing features in non-login shells
#   tmux                       # No histappend - history gets clobbered
#   gnome-terminal             # No aliases - productivity lost
# Problem 2: Redundant work in login shells  
#   ssh user@host              # Sets PATH 5 times (once per sourced file)
# Problem 3: Shell compatibility issues
#  /etc/profile with bashisms  # Breaks when user uses dash, zsh, etc.

# "Your understanding is exactly right: /etc/profile should be the "set it
# once, inherit everywhere" file for process state, while interactive features
# get set fresh in each shell instance."
#
# TODO:
# - this should go in doc/interpreter-state.md
#
# POSIX rule:
# - the file $ENV is sourced for non-interactive shells?
# - bash only
#
# TODO: what are OSH rules?  just ~/.config/oils/oshrc ?  For interactive shells
#
# And then that sources /etc/profile?

show-login-files() {
  # sets $PATH, $PAGER
  # sets umask - for file creation
  # set prompt
  # source .d files
  cat $CHROOT_DIR/etc/profile 
  echo

  ls -l $CHROOT_DIR/etc/profile.d
  echo

  # 00-bashrc - source bashrc
  # locale - CHARSET LANG LC_COLLATE

  head $CHROOT_DIR/etc/profile.d/*
  echo

  # - ONLY for interactive shells
  echo '=== bashrc'
  cat $CHROOT_DIR/etc/bash/bashrc

  # more files
  #ls -l $CHROOT_DIR/etc/bash/*.sh

  #cat $CHROOT_DIR/home/udu/.profile
}

su-demo() {
  sh -c 'echo 1; "$@"' dummy0 printf '%s\n' 'a b' 'c d'
  # same
  sh -c 'echo 1; "$@"' -- printf '%s\n' 'a b' 'c d'

  # wtf man - su takes this over?  this is right
  #su andy sh -c 'echo 1; "$@"' dummy0 printf '%s\n' 'a b' 'c d'

  # AH this is the right way to do it!  Not with sh?
  su andy -- -c 'echo 1; "$@"' dummy0 printf '%s\n' 'a b' 'c d'

  #su andy sh -c 'echo 1; "$@"' -- printf '%s\n' 'a b' 'c d'
}

task-five "$@"
