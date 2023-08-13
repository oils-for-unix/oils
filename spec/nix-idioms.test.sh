## compare_shells: bash
## oils_failures_allowed: 2

#### var ref to array 'preHooks[@]'
#
# This idiom discussed on
# https://github.com/NixOS/nixpkgs/pull/147629

show() {
  echo show

  # These are actually different
  argv.py ${!hooksSlice}

  argv.py ${!hooksSlice+"${!hooksSlice}"}
}

hooksSlice='preHooks[@]'

preHooks=()
show

preHooks=('foo bar' baz)
show

# WTF this exposes a difference?  But not the test case below?

# What's happening here?
# Uncomment this and get an error in bash about hookSlice, even though we never
# undefined it.

#wtf=1
#
# line 6: !hooksSlice: unbound variable

if test -n "$wtf"; then
  # 4.4.0(1)-release
  # echo $BASH_VERSION

  set -u
  preHooks=()
  show

  preHooks=('foo bar' baz)
  show
fi

## STDOUT:
show
[]
[]
show
['foo', 'bar', 'baz']
['foo bar', 'baz']
## END

#### Same as above with set -u
show() {
  echo show

  # bash gives an error here - !hookSlice unbound, even though preHooks exists
  # OSH currently does the "logical" thing
  argv.py ${!hooksSlice}

  argv.py ${!hooksSlice+"${!hooksSlice}"}
}

hooksSlice='preHooks[@]'

set -u
preHooks=()
show

preHooks=('foo bar' baz)
show

## STDOUT:
show
## END
## status: 1


#### ${!ref} to undefined array

set -u
shopt -s eval_unsafe_arith || true 2>/dev/null

#preHooks=()
hookSlice="preHooks[@]"

argv.py ${!hookSlice+"${!hookSlice}"}

for element in ${!hookSlice+"${!hookSlice}"}; do
  echo $element
done

## STDOUT:
[]
## END

#### ${!ref} to undefined string var is fatal, INCONSISTENT with array
hookSlice='preHooks'

argv.py ${!hookSlice}

set -u

argv.py ${!hookSlice}

echo end

## status: 1
## STDOUT:
[]
## END

#### export with dynamic var name +=

orig() {
  export NIX_LDFLAGS${role_post}+=" -L$1/lib64"
}

new() {
  local var_name="NIX_LDFLAGS$role_post"
  local value=" -L$1/lib64"

  eval "$var_name"+='$value'
  export "$var_name"
}

role_post='_foo'

# set -u

if test -n "${BASH_VERSION:-}"; then
  orig one
fi

declare -p NIX_LDFLAGS_foo  # inspect it
unset NIX_LDFLAGS_foo

new one

declare -p NIX_LDFLAGS_foo  # inspect it

## STDOUT:
declare -x NIX_LDFLAGS_foo=" -Lone/lib64"
declare -x NIX_LDFLAGS_foo=" -Lone/lib64"
## END
## OK osh STDOUT:
declare -x NIX_LDFLAGS_foo=' -Lone/lib64'
## END

