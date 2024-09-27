## our_shell: ysh
## oils_failures_allowed: 2

#### global frame doesn't contain builtins like len(), dict()

try {
  pp frame_vars_ | grep -o len
}
pp test_ (_pipeline_status)

## STDOUT:
(List)   [0,1]
## END

#### global frame doesn't contain env vars

try {
  pp frame_vars_ | grep -o TMP
}
pp test_ (_pipeline_status)


## STDOUT:
(List)   [0,1]
## END


