#!/usr/bin/env bash

#### [bash_unset] local-unset / dynamic-unset for localvar
unlocal() { unset -v "$1"; }

f1() {
  local v=local
  unset v
  echo "[$1,local,(unset)] v: ${v-(unset)}"
}
v=global
f1 global

f1() {
  local v=local
  unlocal v
  echo "[$1,local,(unlocal)] v: ${v-(unset)}"
}
v=global
f1 'global'

## STDOUT:
# bash-unset
#   local-unset   = value-unset
#   dynamic-unset = cell-unset
[global,local,(unset)] v: (unset)
[global,local,(unlocal)] v: global
## END

## OK osh/mksh/yash STDOUT:
# always-cell-unset
#   local-unset   = cell-unset
#   dynamic-unset = cell-unset
[global,local,(unset)] v: global
[global,local,(unlocal)] v: global
## END

## OK zsh/ash/dash STDOUT:
# always-value-unset
#   local-unset   = value-unset
#   dynamic-unset = value-unset
[global,local,(unset)] v: (unset)
[global,local,(unlocal)] v: (unset)
## END


#### [bash_unset] local-unset / dynamic-unset for localvar (mutated from tempenv)
unlocal() { unset -v "$1"; }

f1() {
  local v=local
  unset v
  echo "[$1,local,(unset)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

f1() {
  local v=local
  unlocal v
  echo "[$1,local,(unlocal)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

## STDOUT:
# bash-unset (bash-5.1)
#   local-unset   = local-unset
#   dynamic-unset = cell-unset
[global,tempenv,local,(unset)] v: (unset)
[global,tempenv,local,(unlocal)] v: global
## END

## BUG bash STDOUT:
# bash-unset (bash-4.3..5.0 bug)
[global,tempenv,local,(unset)] v: global
[global,tempenv,local,(unlocal)] v: global
## END

## OK osh/mksh/yash STDOUT:
# always-cell-unset
#   local-unset   = cell-unset
#   dynamic-unset = cell-unset
[global,tempenv,local,(unset)] v: tempenv
[global,tempenv,local,(unlocal)] v: tempenv
## END

## OK zsh/ash/dash STDOUT:
# always-value-unset
#   local-unset   = value-unset
#   dynamic-unset = value-unset
[global,tempenv,local,(unset)] v: (unset)
[global,tempenv,local,(unlocal)] v: (unset)
## END


#### [bash_unset] local-unset / dynamic-unset for tempenv
unlocal() { unset -v "$1"; }

f1() {
  unset v
  echo "[$1,(unset)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

f1() {
  unlocal v
  echo "[$1,(unlocal)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

## STDOUT:
# always-cell-unset, bash-unset
#   local-unset   = cell-unset
#   dynamic-unset = cell-unset
[global,tempenv,(unset)] v: global
[global,tempenv,(unlocal)] v: global
## END

## OK zsh/ash/dash/mksh STDOUT:
# always-value-unset, mksh-unset
#   local-unset   = value-unset
#   dynamic-unset = value-unset
[global,tempenv,(unset)] v: (unset)
[global,tempenv,(unlocal)] v: (unset)
## END

#### [bash_unset] function call with tempenv vs tempenv-eval
unlocal() { unset -v "$1"; }

f5() {
  echo "[$1] v: ${v-(unset)}"
  local v
  echo "[$1,local] v: ${v-(unset)}"
  ( unset v
    echo "[$1,local+unset] v: ${v-(unset)}" )
  ( unlocal v
    echo "[$1,local+unlocal] v: ${v-(unset)}" )
}
v=global
f5 'global'
v=tempenv f5 'global,tempenv'
v=tempenv eval 'f5 "global,tempenv,(eval)"'

## STDOUT:
# bash-unset (bash-5.1)
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: (unset)
[global,local+unlocal] v: global
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: global
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: tempenv
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: tempenv
## END

## BUG bash STDOUT:
# bash-unset (bash-4.3..5.0 bug)
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: (unset)
[global,local+unlocal] v: global
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: global
[global,tempenv,local+unlocal] v: global
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: tempenv
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: tempenv
## END

## OK ash STDOUT:
# always-value-unset x init.unset
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: (unset)
[global,local+unlocal] v: (unset)
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: (unset)
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: (unset)
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: (unset)
## END

## OK zsh STDOUT:
# always-value-unset x init.empty
[global] v: global
[global,local] v: 
[global,local+unset] v: (unset)
[global,local+unlocal] v: (unset)
[global,tempenv] v: tempenv
[global,tempenv,local] v: 
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: (unset)
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: 
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: (unset)
## END

## OK dash STDOUT:
# always-value-unset x init.inherit
[global] v: global
[global,local] v: global
[global,local+unset] v: (unset)
[global,local+unlocal] v: (unset)
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: (unset)
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: tempenv
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: (unset)
## END

## OK osh/yash/mksh STDOUT:
# always-cell-unset x init.unset
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: global
[global,local+unlocal] v: global
[global,tempenv] v: tempenv
[global,tempenv,local] v: (unset)
[global,tempenv,local+unset] v: tempenv
[global,tempenv,local+unlocal] v: tempenv
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: (unset)
[global,tempenv,(eval),local+unset] v: tempenv
[global,tempenv,(eval),local+unlocal] v: tempenv
## END


#### [bash_unset] localvar-inherit from tempenv
f1() {
  local v
  echo "[$1,(local)] v: ${v-(unset)}"
}
f2() {
  f1 "$1,(func)"
}
f3() {
  local v=local
  f1 "$1,local,(func)"
}
v=global

f1 'global'
v=tempenv f1 'global,tempenv'
(export v=global; f1 'xglobal')

f2 'global'
v=tempenv f2 'global,tempenv'
(export v=global; f2 'xglobal')

f3 'global'

## STDOUT:
# init.bash
#   init.unset   for local
#   init.inherit for tempenv
[global,(local)] v: (unset)
[global,tempenv,(local)] v: tempenv
[xglobal,(local)] v: (unset)
[global,(func),(local)] v: (unset)
[global,tempenv,(func),(local)] v: tempenv
[xglobal,(func),(local)] v: (unset)
[global,local,(func),(local)] v: (unset)
## END

## OK osh/mksh/yash STDOUT:
# init.unset
[global,(local)] v: (unset)
[global,tempenv,(local)] v: (unset)
[xglobal,(local)] v: (unset)
[global,(func),(local)] v: (unset)
[global,tempenv,(func),(local)] v: (unset)
[xglobal,(func),(local)] v: (unset)
[global,local,(func),(local)] v: (unset)
## END

## OK ash STDOUT:
# init.unset x tempenv-in-localctx
[global,(local)] v: (unset)
[global,tempenv,(local)] v: tempenv
[xglobal,(local)] v: (unset)
[global,(func),(local)] v: (unset)
[global,tempenv,(func),(local)] v: (unset)
[xglobal,(func),(local)] v: (unset)
[global,local,(func),(local)] v: (unset)
## END

## OK zsh STDOUT:
# init.empty
[global,(local)] v: 
[global,tempenv,(local)] v: 
[xglobal,(local)] v: 
[global,(func),(local)] v: 
[global,tempenv,(func),(local)] v: 
[xglobal,(func),(local)] v: 
[global,local,(func),(local)] v: 
## END

## OK dash STDOUT:
# init.inherit
[global,(local)] v: global
[global,tempenv,(local)] v: tempenv
[xglobal,(local)] v: global
[global,(func),(local)] v: global
[global,tempenv,(func),(local)] v: tempenv
[xglobal,(func),(local)] v: global
[global,local,(func),(local)] v: local
## END


#### [bash_unset] nested context by tempenv-eval
f1() {
  local v=local1
  echo "[$1,local1] v: ${v-(unset)}"
  v=tempenv2 eval '
    echo "[$1,local1,tempenv2,(eval)] v: ${v-(unset)}"
    local v=local2
    echo "[$1,local1,tempenv2,(eval),local2] v: ${v-(unset)}"
  '
  echo "[$1,local1] v: ${v-(unset)} (after)"
}
v=global
v=tempenv1 f1 global,tempenv1

## STDOUT:
# localvar-nest yes
[global,tempenv1,local1] v: local1
[global,tempenv1,local1,tempenv2,(eval)] v: tempenv2
[global,tempenv1,local1,tempenv2,(eval),local2] v: local2
[global,tempenv1,local1] v: local1 (after)
## END

## OK mksh/ash/dash/yash STDOUT:
# localvar-nest no
[global,tempenv1,local1] v: local1
[global,tempenv1,local1,tempenv2,(eval)] v: tempenv2
[global,tempenv1,local1,tempenv2,(eval),local2] v: local2
[global,tempenv1,local1] v: local2 (after)
## END

#### [bash_unset] local-unset / dynamic-unset for localvar on nested-context
unlocal() { unset -v "$1"; }

f2() {
  local v=local1
  v=tempenv2 eval '
    local v=local2
    (unset v  ; echo "[$1,local1,tempenv2,(eval),local2,(unset)] v: ${v-(unset)}")
    (unlocal v; echo "[$1,local1,tempenv2,(eval),local2,(unlocal)] v: ${v-(unset)}")
  '
}
v=global
v=tempenv1 f2 global,tempenv1

## STDOUT:
# bash-unset (bash-5.1)
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: (unset)
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: local1
## END

## BUG bash STDOUT:
# bash-unset (bash-4.3..5.0 bug)
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: local1
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: local1
## END

## OK zsh/ash/dash STDOUT:
# always-value-unset
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: (unset)
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: (unset)
## END

## OK osh STDOUT:
# always-cell-unset x localvar-tempenv-share
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: local1
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: local1
## END

## OK mksh/yash STDOUT:
# always-cell-unset (remove all localvar/tempenv)
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: tempenv1
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: tempenv1
## END

#### [bash_unset] dynamic-unset for nested localvars
unlocal() { unset -v "$1"; }

f3() {
  local v=local1
  v=tempenv2 eval '
    local v=local2
    v=tempenv3 eval "
      local v=local3
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)}\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 1)\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 2)\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 3)\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 4)\"
    "
  '
}
v=global
v=tempenv1 f3 global,tempenv1

## STDOUT:
# cell-unset x localvar-tempenv-share x tempenv-in-localctx
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local2 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local1 (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: global (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END

## OK zsh/ash/dash STDOUT:
# value-unset
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END

## OK osh STDOUT:
# cell-unset x localvar-tempenv-share
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local2 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local1 (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: tempenv1 (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: global (unlocal 4)
## END

## OK yash STDOUT:
# cell-unset (remove all localvar)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: tempenv1 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: global (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END

## OK mksh STDOUT:
# cell-unset (remove all localvar/tempenv) x tempenv-value-unset
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: tempenv1 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END


#### [bash_unset] dynamic-unset for nested tempenvs
unlocal() { unset -v "$1"; }

f4_unlocal() {
  v=tempenv2 eval '
    v=tempenv3 eval "
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)}\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 1)\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 2)\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 3)\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 4)\"
    "
  '
}
v=global
v=tempenv1 f4_unlocal global,tempenv1

## STDOUT:
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

## OK zsh/ash/dash/mksh STDOUT:
# value-unset, mksh-unset
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

## OK osh STDOUT:
# cell-unset
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

## OK yash STDOUT:
# remove all tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

#### [bash_unset] local-unset for nested tempenvs
f4_unset() {
  v=tempenv2 eval '
    v=tempenv3 eval "
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)}\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 1)\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 2)\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 3)\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 4)\"
    "
  '
}
v=global
v=tempenv1 f4_unset global,tempenv1

## STDOUT:
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

## OK zsh/ash/dash/mksh/yash STDOUT:
# value-unset, mksh-unset, tempenv-value-unset?
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

## OK osh STDOUT:
# cell-unset
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

## BUG yash STDOUT:
# value-unset? inconsistent with other test cases
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

#### [compat_array] ${arr} is ${arr[0]}
case ${SH##*/} in (dash|ash) exit 1;; esac # dash/ash does not have arrays
case ${SH##*/} in (osh) shopt -s compat_array;; esac
case ${SH##*/} in (zsh) setopt KSH_ARRAYS;; esac
arr=(foo bar baz)
echo "$arr"
## stdout: foo

## N-I dash/ash status: 1
## N-I dash/ash stdout-json: ""

## OK yash stdout: foo bar baz
