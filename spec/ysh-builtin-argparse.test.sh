## our_shell: ysh
## oils_failures_allowed: 2

# Some thoughts before writing code.  Hm can we do this entirely in user code, not as a builtin?
#
# The following is as close as possible to the python argparse which seems to work well

#### Argparse bool option and positional

source --builtin args.ysh

Args :spec {
  flag -v --verbose (Bool)
  arg src
  arg dst
}
var argv = ['-v', 'src/path', 'dst/path']

# Gah we don't have destructuring assignment?
# Also need to define :spec

var arg = parseArgs(spec, argv)

# var arg, i = parseArgs(spec, argv)

json write (arg)
json write (i)
## STDOUT:
{
  "verbose": true,
  "src": "src/path",
  "dst": "dst/path"
}
# TODO: Should this be empty afterwards? Is it even possible with above call?
[

]
## END

#### Argparse basic help message

source --builtin args.ysh

Args :spec {
  description = '''
     Reference Implementation
  '''
  prog = "program-name"

  arg -v --verbose (Bool, help = "Verbose")
  arg src
  arg dst
}
var argv = ['-h', 'src', 'dst']

# Help
var arg = parseArgs(spec, argv)

## STDOUT:
usage: program-name [-h] [-v] src dst

Reference Implementation

positional arguments:
 src
 dst

options:
 -h, --help           show this help message and exit
 -v, --verbose        Verbose
## END
