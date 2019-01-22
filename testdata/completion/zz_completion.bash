# Testing out the "124 protocol" with a dummy 'zz' command.

_zz() {
  COMPREPLY=(z1 z2 z3)
}

complete -F _zz zz
