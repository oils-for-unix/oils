# Test bash and OSH handling of spaces

# This works, you have to escape it FIRST.

# So COMPREPLY takes SHELL-ESCAPED strings
#
# bash does NOT except COMPREPLY -- it expects it to be already escaped.
# But YSH might do so, because it's a better interface.
#
# shopt --set escape_compreply

# This is like 'printf %q' 'cha spaces'
#declare -a commands=( cherry checkout 'cha\ spaces')

# Test apostrophe
#
# Newline works!  It's because printf %q works.  

declare -a commands=( cherry checkout 'cha spaces' "can't" $'one\ntwo')

# This has problems because 'check' is a prefix of two things.
# You might need to add quotes
#declare -a commands=( cherry checkout 'check\ spaces' )

__backslash() {
  #argv "$@"

  local cur=$2

  local -a results

  # Literal spaces don't work, you have to escape them beforehand
  for cmd in "${commands[@]}"; do
    case $cmd in
      $cur*)
        
        # So COMPREPLY is a literal list of SHELL strings, not string argv
        # words

        #local quoted=$(printf %q "$cmd")

        # More efficient version
        local quoted
        printf -v quoted %q "$cmd"

        # This extra space isn't treated as part of the word.  But it does
        # result in an extra space.
        #results+=( "$quoted " )

        results+=( "$quoted" )

        ;;
    esac
  done

  COMPREPLY=( "${results[@]}" )
}

# This works too

__sq() {
  # Important: cur does NOT include the single quote
  local cur=$2

  local -a results

  for cmd in "${commands[@]}"; do
    case $cmd in
      $cur*)
        # Wrong when there's a single quote!
        local quoted="'$cmd'"
        #local quoted="$cmd"
        results+=( "$quoted" )
        ;;
    esac
  done

  COMPREPLY=( "${results[@]}" )
}

# TODO: demonstrate how to get it from an external process
# Well I think the easiest thing is obviously to implement %q on their side,
# and '\n'

b-argv() {
  python3 -c 'import sys; print(sys.argv[1:])' "$@"
}

sq-argv() {
  b-argv "$@"
}

complete -F __backslash b-argv
complete -F __sq sq-argv

