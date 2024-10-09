# spec/ysh-stdlib

## our_shell: ysh

#### smoke test for two.sh

source --builtin osh/two.sh

log 'hi'

set +o errexit
( die "bad" )
echo status=$?

## STDOUT:
status=1
## END

#### smoke test for stream.ysh and table.ysh 

shopt --set redefine_proc_func   # byo-maybe-main

source $LIB_YSH/stream.ysh
source $LIB_YSH/table.ysh

## status: 0

