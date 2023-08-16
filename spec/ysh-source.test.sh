# spec/ysh-source

## our_shell: ysh
## oils_failures_allowed: 0

#### --builtin flag
source --builtin stdlib/math.ysh

json write (max(1, 2))
## STDOUT:
2
## END

#### no path passed with --builtin flag
source --builtin
## status: 2
## STDOUT:
## END

#### non-existant path passed to --builtin flag
source --builtin test/this-file-will-never-exist.ysh
## status: 2
## STDOUT:
## END
