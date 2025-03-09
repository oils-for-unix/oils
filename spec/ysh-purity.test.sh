## our_shell: ysh

# Disallow:
#   Executor:
#      external, command sub, process sub, pipeline, redirect
#   YSH APIs: io and vm
#   $RANDOM $SECONDS
#   builtins - readarray, mapfile, trap?
#   Running traps?  Yes!  Because this could be an "escape"
#
# Not disallowed:
#   setglobal, mutating arguments with setvar

#### Can't run command sub

echo >impure.ysh 'var x = $(echo command sub)'

$[ENV.SH] --eval impure.ysh -c 'echo $x'
$[ENV.SH] --eval-pure impure.ysh -c 'echo hi'

## status: 1
## STDOUT:
command sub
## END
