source $REPO_ROOT/spec/testdata/bash-source-2.sh

shopt -s extdebug

add () { expr 4 + 4; }

declare -F 
echo

declare -F add
# in bash-source-2
declare -F g | sed "s;$REPO_ROOT;ROOT;g"
