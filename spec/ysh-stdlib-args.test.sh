## our_shell: ysh
## oils_failures_allowed: 1

#### args.ysh example usage
source --builtin args.ysh

parser (&spec) {
  flag -v --verbose (help="Verbosely")  # default is Bool, false

  flag -P --max-procs ('int', default=-1, help='''
    Run at most P processes at a time
    ''')

  flag -i --invert ('bool', default=true, help='''
    Long multiline
    Description
    ''')

  arg src (help='Source')
  arg dest (help='Dest')

  rest files
}

var args = parseArgs(spec, :| mysrc -P 12 mydest a b c |)

echo "Verbose $[args.verbose]"
pp line (args)
## STDOUT:
Verbose false
(Dict)   {"src":"mysrc","max-procs":12,"dest":"mydest","files":["a","b","c"],"verbose":false,"invert":true}
## END

#### Bool flag, positional args, more positional

source --builtin args.ysh

parser (&spec) {
  flag -v --verbose ('bool')
  arg src
  arg dst

  rest more  # allow more args
}
#json write (spec)

var argv = ['-v', 'src/path', 'dst/path', 'x', 'y', 'z']

var args = parseArgs(spec, argv)

pp line (args)

if (args.verbose) {
  echo "$[args.src] -> $[args.dst]"
  write -- @[args.more]
}

## STDOUT:
(Dict)   {"verbose":true,"src":"src/path","dst":"dst/path","more":["x","y","z"]}
src/path -> dst/path
x
y
z
## END

#### Test multiple ARGVs against a parser

source --builtin args.ysh

parser (&spec) {
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
  var args_str = join(args, ' ')
  echo "----------  $args_str  ----------"
  echo "\$ bin/ysh example.sh $args_str"
  pp line (parseArgs(spec, args))

  echo
}
## STDOUT:
----------  -v --count 120 example.sh  ----------
$ bin/ysh example.sh -v --count 120 example.sh
(Dict)   {"verbose":true,"count":120,"file":"example.sh"}

----------  -v --count 120 example.sh -v  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v
(Dict)   {"verbose":true,"count":120,"file":"example.sh"}

----------  -v --count 120 example.sh -v --count 150  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v --count 150
(Dict)   {"verbose":true,"count":150,"file":"example.sh"}

## END

#### Basic help message

source --builtin args.ysh

parser (&spec) {
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
var args = parseArgs(spec, argv)

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
    {short: '-v', long: '--verbose', name: 'verbose', type: null, default: '', help: 'Enable verbose logging'},
    {short: '-c', long: '--count', name: 'count', type: 'int', default: 80, help: 'Maximum line length'},
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
(Dict)   {"verbose":true,"count":120,"file":"example.sh"}

$ python3 example.py -v --count 120 example.sh
Namespace(filename='example.sh', count='120', verbose=True)

----------  -v --count 120 example.sh -v  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v
(Dict)   {"verbose":true,"count":120,"file":"example.sh"}

$ python3 example.py -v --count 120 example.sh -v
Namespace(filename='example.sh', count='120', verbose=True)

----------  -v --count 120 example.sh -v --count 150  ----------
$ bin/ysh example.sh -v --count 120 example.sh -v --count 150
(Dict)   {"verbose":true,"count":150,"file":"example.sh"}

$ python3 example.py -v --count 120 example.sh -v --count 150
Namespace(filename='example.sh', count='150', verbose=True)

## END

#### Define spec and print it

source --builtin args.ysh

parser (&spec) {
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
      "name": "verbose",
      "type": "bool",
      "default": false,
      "help": null
    }
  ],
  "args": [
    {
      "name": "src",
      "help": null
    },
    {
      "name": "dst",
      "help": null
    }
  ],
  "rest": "more"
}
## END

#### Default values
source --builtin args.ysh

parser (&spec) {
  flag -S --sanitize ('bool', default=false)
  flag -v --verbose ('bool', default=false)
  flag -P --max-procs ('int')  # Will set to null (the default default)
}

var args = parseArgs(spec, [])

pp line (args)
## STDOUT:
(Dict)   {"sanitize":false,"verbose":false,"max-procs":null}
## END

#### Duplicate argument/flag names
source --builtin args.ysh

try {
  parser (&spec) {
    flag -n --name
    flag -N --name
  }
}
echo status=$_status

try {
  parser (&spec) {
    flag -n --name
    arg name
  }
}
echo status=$_status

try {
  parser (&spec) {
    arg name
    flag -o --other
    arg name
  }
}
echo status=$_status
## STDOUT:
status=3
status=3
status=3
## END

#### Error cases
source --builtin args.ysh

parser (&spec) {
  flag -v --verbose
  flag -n --num ('int', required=true)

  arg action
  arg other (required=false)
}

try { call parseArgs(spec, :| -n 10 action other extra |) }
echo status=$_status

try { call parseArgs(spec, :| -n |) }
echo status=$_status

try { call parseArgs(spec, :| -n -v |) }
echo status=$_status

try { = parseArgs(spec, :| -n 10 |) }
echo status=$_status

try { call parseArgs(spec, :| -v action |) }
echo status=$_status

try { call parseArgs(spec, :| --unknown |) }
echo status=$_status
## STDOUT:
status=2
status=2
status=2
status=2
status=2
status=2
## END
