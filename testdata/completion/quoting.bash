# Test bash and OSH handling of spaces

# This works, you have to escape it FIRST.

# So COMPREPLY takes SHELL-ESCAPED strings
#
# bash does NOT quote COMPREPLY -- it expects it to be already quoted.
#
# But YSH might do so, because it's a better interface.
#
# shopt --set ysh_quotes_compreply
#
# If the user plugin doesn't quote it, then the shell is responsible for it.

# This is like 'printf %q' 'cha spaces'
#declare -a commands=( cherry checkout 'cha\ spaces')

# Test apostrophe
#
# Newline works!  It's because printf %q works.  

# The $ gets quoted
# BUG: bash shows \$file_not_var as a completion candidate, but you can't select it
#
# - If you type $, you get $'one\ntwo'
# - If you type \$, you get $'one\ntwo' as well
# This is probably GNU readline evaluation
# 
# This is why YSH distinguishes between completing the shell language, and
# completing a command arg.  The latter must be shell-quoted.

declare -a commands=(
  cherry checkout
  'file with space'
  "can't"  # apostrophe
  $'one\ntwo'  # newline
  '$file_not_var'
  $'mu \u03bc \u4e09 \U0001f618 unicode'
)

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

argv() {
  python3 -c 'import sys; print(sys.argv[1:])' "$@"
}

b-argv() {
  argv "$@"
}

sq-argv() {
  argv "$@"
}

w1-argv() {
  argv "$@"
}

w2-argv() {
  argv "$@"
}

c-argv() {
  argv "$@"
}

cw-argv() {
  argv "$@"
}

q2-argv() {
  argv "$@"
}

q3-argv() {
  argv "$@"
}

v-argv() {
  argv "$@"
}

complete -F __backslash b-argv
complete -F __sq sq-argv

# Hm this doesn't work.  It comes across as one candidate.
# But it doesn't get shell escaping
#complete -W 'word\ with\ spaces w2' w-argv

# It comes across as one candidate
complete -W "'word with spaces' w2" w1-argv

# This works!  I think there is a double-eval
complete -W "'word\ with\ spaces' w2" w2-argv

print-comps() {
  local cur=$2

  for cmd in "${commands[@]}"; do
    case $cmd in
      $cur*)
        # More efficient version
        local quoted
        printf -v quoted %q "$cmd"
        echo "$quoted"
        ;;
    esac
  done
}

complete -C print-comps c-argv

#
# Try to figure out what -W does
#

# This doesn't work
complete -W '$(print-comps)' cw-argv

# Doesn't work either
#complete -W "$(print-comps)" cw-argv

print-comps-q2() {
  print-comps | while read -r line; do
    printf '%q\n' "$line"
  done
}

# This works except you have to press $ for $'one\ntwo'
complete -W "$(print-comps-q2)" q2-argv

# -W is first split by IFS, and then each word is evaluated?

print-comps-q3() {
  ### Complex alternative to printf %q that also works

  print-comps | while read -r line; do
    # This is wrong
    #echo "'$line'"

    # replace '  -->  '\''
    echo "'${line//"'"/"'\\''"}'"
  done
}

test-words() {
  echo "$(print-comps)"
  echo
  echo "$(print-comps-q2)"
  echo
  echo "$(print-comps-q3)"
  echo

  echo 'Unquoted command sub, with word splitting'
  echo

  echo $(print-comps-q2)
  echo

  echo $(print-comps-q3)
  echo
}

# This works except you have to press $ for $'one\ntwo'
complete -W "$(print-comps-q3)" q3-argv


print-vars-with-dollar() {
  local prefix=$1
  compgen -A variable "$prefix" | while read -r line; do
    echo '$'$line
  done
}

__complete-vars() {
  #argv "$@"
  local cur=$2

  local -a results

  case $cur in
    '$'*)
      local prefix=${cur:1}
      #echo "prefix=$prefix"

      # Variables that start with prefix
      COMPREPLY=( $(print-vars-with-dollar "$prefix") )
      ;;
  esac
}

complete -F __complete-vars v-argv


# For testing print-comps

if test "$(basename -- $0)" = 'quoting.bash'; then
  "$@"
fi

