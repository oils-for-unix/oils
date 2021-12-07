# Common functions for soil/

log() {
  echo "$@" 1>&2
}

dump-env() {
  env | grep -v '^encrypted_' | sort
}
