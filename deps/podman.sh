#!/usr/bin/env bash
#
# podman on Debian 12, instead of Docker
#
# Usage:
#   deps/podman.sh <function name>


write-config() {
  mkdir -p ~/.config/containers
  cat > ~/.config/containers/registries.conf <<'EOF'
unqualified-search-registries = ['docker.io']
EOF
}

export-podman() {
  export DOCKER=podman

  # https://docs.podman.io/en/latest/markdown/podman.1.html
  export CONTAINERS_REGISTRIES_CONF=~/.config/containers/registries.conf

  # For some reason it uses /run/user/1000/containers by default
  export REGISTRY_AUTH_FILE=~/.config/containers/auth.json
}

login() {
  export-podman

  # type password on stdin
  sudo -E podman login -u oilshell --password-stdin
}

test-image-stats() {
  # Hm on Github Actions, images-layers.tsv comes up empty?
  # The text file works though
  # It works on sourcehut with the cpp-tarball task

  which podman
  podman --version
  echo

  soil/host-shim.sh save-image-stats '' podman '' ''

  #soil/host-shim.sh image-layers-tsv podman '' ''
}

if test $(basename $0) = 'podman.sh'; then
  "$@"
fi
