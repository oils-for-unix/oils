f() {
  echo 'F'
  ZZ=zz g
  #g
}

g() {
  echo 'G'

  local n=${#BASH_SOURCE[@]}
  for (( i = 0; i < n; ++i)); do
    local src=${BASH_SOURCE[i]}

    echo "STACK:$src:${FUNCNAME[i]}:${BASH_LINENO[i]}"
  done
}

# TODO: enable these frames
YY=yy f
#f

# These are wrong
#set -x
#PS4='${BASH_SOURCE[0]}:${BASH_LINENO[0]}:'
#PS4='${BASH_SOURCE[-1]}:${BASH_LINENO[-1]}:'

