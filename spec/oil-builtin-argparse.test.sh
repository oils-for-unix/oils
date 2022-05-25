# oil-builtin-argparse
#
# Some thoughts before writing code.  Hm can we do this entirely in user code, not as a builtin?
#
# I think it modifies OPT


#### Argparse Prototype

hay define argparse

# Oops, we're running into this problem ...

hay define argparse/flag

# This means we need expr.Type objects?  

argparse foo {
  flag -v --verbose (Bool) {
    help = 'fo'
    default = true
  }

  flag -h --help (Bool) {
    help = 'fo'
  }

  arg name (pos = 1) {
    foo
  }
}

## STDOUT:
TODO
## END
