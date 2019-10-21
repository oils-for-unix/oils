#!/bin/bash
#
# Usage:
#   ./nix.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# This is a 66-line bootstrap script.
download() {
  wget --directory _tmp https://nixos.org/nix/install
  chmod +x _tmp/install
}

# Usage: . test/nix.sh env
env() {
  set +o nounset
  set +o pipefail
  set +o errexit
  . /home/andy/.nix-profile/etc/profile.d/nix.sh
}

"$@"
