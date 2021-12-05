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

## STDOUT:
show
[]
[]
show
['foo', 'bar', 'baz']
['foo bar', 'baz']
## END
