#!/bin/bash
#
# Usage:
#   ./gdbgui.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# This leads to a Python 2/3 problem!  Need pipx.
bare_install() {
  pip install gdbgui
}

# https://www.gdbgui.com/installation/

install-pipx() {
  python3 -m pip install --user pipx

  # This modifies ~/.bash_profile, gah
  #python3 -m userpath append ~/.local/bin
}

install() {
  ~/.local/bin/pipx install gdbgui
}

run() {
  ~/.local/bin/pipx run gdbgui
}

# Not working!
#
# No gdb response received after 10 seconds.
#
# Possible reasons include:
# 1) gdbgui, gdb, or the debugged process is not running.

# 2) gdb or the inferior process is busy running and needs to be interrupted
# (press the pause button up top).

# 3) Something is just taking a long time to finish and respond back to this
# browser window, in which case you can just keep waiting.


# TODO: Try this.
#
# Rename to devtools/debugger.sh 

# https://github.com/VSCodium/vscodium/releases

"$@"
