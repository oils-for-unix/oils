# oil-builtin-argparse
#
# Some thoughts before writing code.  Hm can we do this entirely in user code, not as a builtin?
#
# The following is as close as possible to the python argparse which seems to work well

#### Argparse basic statement

#I assume the hay definitions are given.
ArgSpec myspec {
  description = '''
     Reference Implementation
  '''
  arg -v --verbose { type = Bool, help = "Verbose" }
  # TODO: can position be implicit (in given order?) or is the order not maintained in hay?
  arg firstPositional
}
var args = ['-v' 'argument']
argparse (myspec, args, :opts)

= opts
= args
## STDOUT:
(OrderedDict)   <'verbose': True, 'firstPositional': 'argument'> 
# TODO: Should this be empty afterwards? Is it even possible with above call?
(List)   []
## END

#### Argparse print automatic option "help"
ArgSpec myspec {
  description = '''
     Reference Implementation
  '''
  prog = "program-name"
  arg -v --verbose { type = Bool, help = "Verbose" }
  arg firstPositional
}
var args = ['-h' 'posone']

argparse (myspec, args, :opts)
## STDOUT:
usage: program-name [-h] [-v] firstPositional

Reference Implementation

positional arguments:
 firstPositional

options:
 -h, --help           show this help message and exit
 -v, --verbose        Verbose
## END
