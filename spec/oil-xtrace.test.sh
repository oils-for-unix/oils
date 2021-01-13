# Oil xtrace

#### proc
shopt --set xtrace xtrace_rich

proc f {
  : $1
}
f hi
## STDOUT:
## END

# TODO: consider not quoting ':' and FOO=bar?  And set '+x' doesn't need to be
# quoted?  Only space does

## STDERR:
+ f hi
  > proc f
  + ':' hi
  < proc f
## END
