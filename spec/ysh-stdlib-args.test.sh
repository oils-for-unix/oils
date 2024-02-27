## our_shell: ysh
## oils_failures_allowed: 1

#### Bool flag, positional args, more positional

source --builtin args.ysh

arg-parse (&spec) {
  flag -v --verbose ('bool')
  arg src
  arg dst

  rest more  # allow more args
}
#json write (spec)

var argv = ['-v', 'src/path', 'dst/path', 'x', 'y', 'z']

var arg, i = parseArgs(spec, argv)

pp line (arg)
pp line (i)

if (arg.verbose) {
  echo "$[arg.src] -> $[arg.dst]"
  write -- @[arg.more]
}

## STDOUT:
(Dict)   {"verbose":true,"src":"src/path","dst":"dst/path","more":["x","y","z"]}
(Int)   6
src/path -> dst/path
x
y
z
## END

#### Test multiple command lines against a parser

source --builtin args.ysh

arg-parse (&spec) {
  flag -v --verbose ('bool', false)
  flag -c --count ('int', 120)
  arg file
}

var argsCases = [
  :| -v --count 120 example.sh |,
  :| -v --count 120 example.sh -v |,  # duplicate flags are ignored
  :| -v --count 120 example.sh -v --count 150 |,  # the last duplicate has precedence
]

for args in (argsCases) {
  var args_str = join(args, ' ')
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

#### Basic help message

source --builtin args.ysh

arg-parse (&spec) {
  # TODO: implement description, prog and help message
  description '''
     Reference Implementation
  '''
  prog "program-name"

  arg -v --verbose (Bool, help = "Verbose")
  arg src
  arg dst
}
var argv = ['-h', 'src', 'dst']

# Help
var arg, _ = parseArgs(spec, argv)

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

#### Compare parseArgs() vs Python argparse

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

#### Define spec and print it

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

