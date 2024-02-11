## our_shell: ysh
## oils_failures_allowed: 1

# Can we do this entirely in user code, not as a builtin?
#
# The following is as close as possible to the python argparse which seems to work well

#### Argparse bool option and positional

source --builtin args.ysh

arg-parse (&spec) {
  flag -v --verbose ('bool')
  arg src
  arg dst

  rest more  # allow more args
}
#json write (spec)

var argv = ['-v', 'src/path', 'dst/path']

# TODO: need destructuring with var
# var arg, i = parseArgs(spec, argv)

var result = parseArgs(spec, argv)
setvar arg, i = result

json write --pretty=F (arg)
json write (i)
## STDOUT:
{"verbose":true,"src":"src/path","dst":"dst/path","more":[]}
3
## END

#### Argparse basic help message

source --builtin args.ysh

arg-parse (&spec) {
  # TODO: implement description, prog and help message
  description '''
     Reference Implementation
  '''
  prog-name "program-name"

  flag -v --verbose ('bool', help="Verbose", default=false)
  flag -n --count ('int')
  arg src
  arg dst
}
var argv = ['-h', 'src', 'dst']

# Help
var arg = parseArgs(spec, argv)

## STDOUT:
usage: program-name [-h] [-v] -n src dst

   Reference Implementation

Positional Arguments:
 src
 dst

Flags:
 -h, --help		Show this help message and exit
 -v, --verbose		Verbose
 -n, --count
## END

#### Parse args using a JSON argspec

source --builtin args.ysh

var spec = {
  flags: [
    {short: '-v', long: '--verbose', type: null, default: '', help: 'Enable verbose logging'},
    {short: '-c', long: '--count', type: 'int', default: 80, help: 'Maximum line length'},
  ],
  args: [
    {name: 'file', type: 'str', help: 'File to check line lengths of'}
  ],
  rest: null,
}

var argsCases = [
  :| -v --count 120 example.sh |,
  :| -v --count 120 example.sh -v |,  # duplicate flags are ignored
  :| -v --count 120 example.sh -v --count 150 |,  # the last duplicate has precedence
]

var argparse_py = '''
import argparse
import sys

spec = argparse.ArgumentParser()
spec.add_argument("filename")
spec.add_argument("-c", "--count")
spec.add_argument("-v", "--verbose",
                  action="store_true")

result = spec.parse_args(sys.argv[1:])
print(result)
'''

for args in (argsCases) {
  var args_str = args->join(" ")
  echo "----------  $args_str  ----------"
  echo "\$ bin/ysh example.sh $args_str"
  pp line (parseArgs(spec, args))

  echo
  echo "\$ python3 example.py $args_str"
  python3 -c $argparse_py @args

  echo
}
## STDOUT:
----------  -v --count 120 example.sh  ----------
$ bin/ysh example.sh -v --count 120 example.sh
(List)   [{"verbose":true,"count":120,"file":"example.sh"},4]

$ python3 example.py -v --count 120 example.sh
Namespace(filename='example.sh', count='120', verbose=True)

----------  -v --count 120 example.sh -v  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v
(List)   [{"verbose":true,"count":120,"file":"example.sh"},5]

$ python3 example.py -v --count 120 example.sh -v
Namespace(filename='example.sh', count='120', verbose=True)

----------  -v --count 120 example.sh -v --count 150  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v --count 150
(List)   [{"verbose":true,"count":150,"file":"example.sh"},7]

$ python3 example.py -v --count 120 example.sh -v --count 150
Namespace(filename='example.sh', count='150', verbose=True)

## END

#### Args spec definitions

source --builtin args.ysh

arg-parse (&spec) {
  flag -v --verbose ('bool')
  arg src
  arg dst

  rest more  # allow more args
}

json write (spec)
## STDOUT:
{
  "flags": [
    {
      "short": "-h",
      "long": "--help",
      "type": "bool",
      "default": false,
      "help": "Show this help message and exit"
    },
    {
      "short": "-v",
      "long": "--verbose",
      "type": "bool",
      "default": null,
      "help": null
    }
  ],
  "args": [
    {
      "name": "src",
      "default": null,
      "help": null
    },
    {
      "name": "dst",
      "default": null,
      "help": null
    }
  ],
  "rest": "more"
}
## END

#### Args spec definitions driving argument parser

source --builtin args.ysh

arg-parse (&spec) {
  flag -v --verbose ('bool', default=false)
  flag -c --count ('int', default=120)
  arg file
}

var argsCases = [
  :| -v --count 120 example.sh |,
  :| -v --count 120 example.sh -v |,  # duplicate flags are ignored
  :| -v --count 120 example.sh -v --count 150 |,  # the last duplicate has precedence
]

for args in (argsCases) {
  var args_str = args->join(" ")
  echo "----------  $args_str  ----------"
  echo "\$ bin/ysh example.sh $args_str"
  pp line (parseArgs(spec, args))

  echo
}
## STDOUT:
----------  -v --count 120 example.sh  ----------
$ bin/ysh example.sh -v --count 120 example.sh
(List)   [{"verbose":true,"count":120,"file":"example.sh"},4]

----------  -v --count 120 example.sh -v  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v
(List)   [{"verbose":true,"count":120,"file":"example.sh"},5]

----------  -v --count 120 example.sh -v --count 150  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v --count 150
(List)   [{"verbose":true,"count":150,"file":"example.sh"},7]

## END
