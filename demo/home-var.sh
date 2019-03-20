#!/bin/bash
#
# Where does $HOME come from?
#
# Usage:
#   ./home-var.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# In the bash source, it appears to be set in a login shell?  But I don't seem
# to be able to tickle that line.
#
# in variables.c, initialize_shell_variables():
#
# if (login_shell == 1 && posixly_correct == 0)
#   set_home_var ();
         
test-bash() {
  set +o errexit

  #local sh=bash
  local sh=_tmp/spec-bin/bash

  local prog='echo home=$HOME'
  env -i -- $sh -c "$prog"
  env -i -- $sh -i -c "$prog"
  env -i -- $sh --login -c "$prog"
  env -i -- $sh --login -i -c "$prog"
  env -i -- $sh --norc --login -c "$prog"

  local prog='echo HOME=; env | grep HOME'
  # Test if exported
  env -i -- $sh -c "$prog"
  env -i -- $sh -i -c "$prog"
  env -i -- $sh --login -c "$prog"
  env -i -- $sh --login -i -c "$prog"
  env -i -- $sh --norc --login -c "$prog"
}

# ANSWER:

# https://unix.stackexchange.com/questions/123858/is-the-home-environment-variable-always-set-on-a-linux-system

# The POSIX specification requires the OS to set a value for $HOME
#
# HOME
# The system shall initialize this variable at the time of login to be a
# pathname of the user's home directory. See <pwd.h>.

# https://superuser.com/questions/271925/where-is-the-home-environment-variable-set
# 
# - by login on console, telnet and rlogin sessions
# - by sshd for SSH connections
# - by gdm, kdm or xdm for graphical sessions.
#
# This is annoying since the cron environment doesn't have it!  But it looks
# like it shouldn't be fixed in the shell.

"$@"
