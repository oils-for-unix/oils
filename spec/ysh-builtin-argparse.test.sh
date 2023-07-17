## our_shell: ysh
## oils_failures_allowed: 2

# Some thoughts before writing code.  Hm can we do this entirely in user code, not as a builtin?
#
# The following is as close as possible to the python argparse which seems to work well

#### Argparse bool option and positional

hay define ArgSpec
hay define ArgSpec/Arg

ArgSpec myspec {
  Arg -v --verbose { type = Bool }
  Arg src
  Arg dst
}
var args = ['-v', 'src/path', 'dst/path']
argparse (myspec, args, :opts)

json write (opts)
json write (args)
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
hay define ArgSpec
hay define ArgSpec/Arg

ArgSpec myspec {
  description = '''
     Reference Implementation
  '''
  prog = "program-name"
  Arg -v --verbose { type = Bool; help = "Verbose" }
  Arg src
  Arg dst
}
var args = ['-h', 'src', 'dst']

argparse (myspec, args, :opts)
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
