# spec/ysh-funcs

## our_shell: ysh
## oils_failures_allowed: 0

#### Identity function
func identity(x) {
  return (x)
}

= identity("ysh")
## STDOUT:
(Str)   'ysh'
## END
