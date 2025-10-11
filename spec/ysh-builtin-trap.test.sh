## our_shell: ysh

#### trap --remove INT EXIT

trap 'echo hi' INT EXIT HUP
trap -p
echo ---

trap --remove INT EXIT
trap -p

## STDOUT:
trap -- 'echo hi' EXIT
trap -- 'echo hi' SIGHUP
trap -- 'echo hi' SIGINT
---
trap -- 'echo hi' SIGHUP
## END
