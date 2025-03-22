## compare_shells: bash-4.4 zsh mksh ash dash yash
## oils_failures_allowed: 5

# Some tests moved here for spec/ble-features
# We could move others too

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

## OK zsh/ash/dash/mksh STDOUT:
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

