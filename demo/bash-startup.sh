#!/bin/bash
#
# Usage:
#   ./startup.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html

# Looks at /etc/profile first, which is documented.
login-shell() {
  strace -e open bash --login
}

# Looks at /etc/bash.bashrc first.  How does it find this?
regular-shell() {
  strace -e open bash
}

# OK it's in here, but I don't see it documented.  Is it Debian-specific?

# In config-top.sh in the bash tree, I see this.  So Debian must turn this on.
#
# /* System-wide .bashrc file for interactive shells. */
# /* #define SYS_BASHRC "/etc/bash.bashrc" */ 
search-bin() {
  strings /bin/bash | grep bashrc
}

"$@"
