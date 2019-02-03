_bad() {
  #argv "$@"

  echo '_bad returning 124'

  # This caused an infinite loop in OSH, but not in bash.  We have to test if
  # the return value is 124 AND the compspec was updated.
  #
  # In bash, it seems like you EITHER set COMPREPLY or return 124, not BOTH!
  # If it sees 124, it doesn't process the completions (unlike OSH at the
  # moment).

  #COMPREPLY=(x y)

  return 124
}
complete -F _bad bad

_both() {
  #echo '_both setting COMPREPLY and returning 124'
  COMPREPLY=(x y)
  return 124
}
complete -F _both both

_both2() {
  #echo '_both setting COMPREPLY and returning 124'
  COMPREPLY=(x y)
  complete -W 'b1 b2' both2
  return 124
}
complete -F _both2 both2

_default() {
  echo '_default returning 124 without changing completion spec'
  # We're supposed to source something here, but we didn't
  return 124
}

complete -F _default -D
