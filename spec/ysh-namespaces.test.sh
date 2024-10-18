## our_shell: ysh
## oils_failures_allowed: 1

#### global frame doesn't contain builtins like len(), dict(), io

try {
  pp frame_vars_ | grep -o len
}
pp test_ (_pipeline_status)

try {
  pp frame_vars_ | grep -o dict
}
pp test_ (_pipeline_status)

try {
  pp frame_vars_ | grep -o -w io
}
pp test_ (_pipeline_status)

## STDOUT:
(List)   [0,1]
(List)   [0,1]
(List)   [0,1]
## END

#### global frame doesn't contain env vars

#pp frame_vars_

try {
  pp frame_vars_ | grep -o TMP
}
pp test_ (_pipeline_status)


## STDOUT:
(List)   [0,1]
## END

#### __builtins__ module

var b = len(propView(__builtins__))

# more than 30 builtins
assert [b > 30]

var mylist = :| a b |

setvar len = 4  # overwrite
setvar len = __builtins__.len(mylist)
assert [2 === len]

## STDOUT:
## END

