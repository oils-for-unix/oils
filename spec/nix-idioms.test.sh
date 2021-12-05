#### var ref to array 'preHooks[@]'
#
# This idiom discussed on
# https://github.com/NixOS/nixpkgs/pull/147629

shopt -s eval_unsafe_arith  # required for OSH

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

  # These are actually different
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


#### Undefined array

set -u
shopt -s eval_unsafe_arith || true 2>/dev/null

hookSlice="preHooks[@]"

argv.py ${!hookSlice+"${!hookSlice}"}

for element in ${!hookSlice+"${!hookSlice}"}; do
  echo $element
done

## STDOUT:
[]
## END
