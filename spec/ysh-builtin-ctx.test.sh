## our_shell: ysh
## oils_failures_allowed: 0

#### ctx push and set
var mydict = {}
ctx push (mydict) {
  ctx set (key1="value1")
  ctx set (key2="value2")
}
json write (mydict)
## STDOUT:
{
  "key1": "value1",
  "key2": "value2"
}
## END

#### ctx emit
var p = {}
ctx push (p) {
  ctx emit flag ({short_name: '-v'})
  # p => {'flag': [{short_name: '-v'}]}
  json write (p)

  ctx emit flag ({short_name: '-c'})
  # p => {'flag': [{short_name: '-v'}, {short_name: '-c'}]}
  json write (p)
}
json write (p)
## STDOUT:
{
  "flag": [
    {
      "short_name": "-v"
    }
  ]
}
{
  "flag": [
    {
      "short_name": "-v"
    },
    {
      "short_name": "-c"
    }
  ]
}
{
  "flag": [
    {
      "short_name": "-v"
    },
    {
      "short_name": "-c"
    }
  ]
}
## END

#### mini-argparse
proc parser (; place ; ; block_def) {    # place for parser, and block arg
  var p = {}  # "flag spec", maybe call it parser now
  ctx push (p) {
    eval (block_def)
    # the eval "expands" to calls like this:
    # ctx emit flag ({short_name: '-v', long_name: '--verbose'})  # flag -v --verbose
    # ctx emit flag ({long_name: '--count', type: Int, help: 'z'})  # flag --count (Int, help='z')
    # ctx emit arg (name: 'src')  # arg src
  }
  call place->setValue(p)  # "return" the parser we constructed
}

proc flag (short_name, long_name; type; help) {
  ctx emit flag ({short_name, long_name, type, help})  # using "punning"
}

proc arg (name) {
  ctx emit arg ({name})
}

var Bool = "Bool"

parser (&spec) {  # call proc parser with place and block
  flag -t --tsv (Bool, help='')
  flag -r --rusage (Bool, help='')
  arg file
}
json write (spec)
## STDOUT:
{
  "flag": [
    {
      "short_name": "-t",
      "long_name": "--tsv",
      "type": "Bool",
      "help": ""
    },
    {
      "short_name": "-r",
      "long_name": "--rusage",
      "type": "Bool",
      "help": ""
    }
  ],
  "arg": [
    {
      "name": "file"
    }
  ]
}
## END
