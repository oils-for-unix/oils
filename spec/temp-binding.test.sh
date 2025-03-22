## compare_shells: bash zsh mksh ash
## oils_failures_allowed: 2

# forked from spec/ble-idioms
# the IFS= eval 'local x' bug

#### More eval 'local v='
case $SH in mksh) exit ;; esac

set -u

f() {
  # The temp env messes it up
  tmp1= local x=x
  tmp2= eval 'local y=y'

  # similar to eval
  tmp3= . $REPO_ROOT/spec/testdata/define-local-var-z.sh

  # Bug does not appear with only eval
  #eval 'local v=hello'

  #declare -p v
  echo x=$x
  echo y=$y
  echo z=$z
}

f 

## STDOUT:
x=x
y=y
z=z
## END

## N-I mksh STDOUT:
## END

#### Temp bindings with local

f() {
  local x=x
  tmp='' local tx=tx

  # Hm both y and ty persist in bash/zsh
  eval 'local y=y'
  tmp='' eval 'local ty=ty'

  # Why does this have an effect in OSH?
  if true; then
    x='' unset x
    tx='' unset tx
    y='' unset y
    ty='' unset ty
  fi

  #unset y
  #unset ty

  echo x=$x
  echo tx=$tx
  echo y=$y
  echo ty=$ty
}

f

## STDOUT:
x=x
tx=tx
y=y
ty=ty
## END

## BUG mksh/ash STDOUT:
x=
tx=
y=
ty=
## END

#### Temp bindings with unset 

# key point:
# unset looks up the stack
# local doesn't though

x=42
unset x
echo x=$x

echo ---

x=42
tmp= unset x
echo x=$x

x=42
tmp= eval 'unset x'
echo x=$x

echo ---

shadow() {
  x=42
  x=tmp unset x
  echo x=$x
  
  x=42
  x=tmp eval 'unset x'
  echo x=$x
}

shadow

echo ---

case $SH in
  bash) set -o posix ;;
esac
shadow

# Now shadow

# unset is a special builtin
# type unset

## STDOUT:
x=
---
x=
x=
---
x=42
x=42
---
x=42
x=42
## END

## BUG mksh/ash/dash STDOUT:
x=
---
x=
x=
---
x=
x=
---
x=
x=
## END
