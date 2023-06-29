# spec/oil-case

#### case syntax, one line
const x = "header.h"
case (x) {
  *.h | *.cc { echo C++ }
  *.py       { echo Python }
}

# not recommended, but it works
case (x) { header.h { echo header.h } * { echo other } }

## status: 0
## STDOUT:
C++
header.h
## END

#### case syntax, multiline
const x = "hello.py"
case (x) {
  *.h | *.cc {
    echo C++
    echo 2; echo 3
  }
  *.py {
    echo \
      Python
  }
}
## status: 0
## STDOUT:
Python
## END

#### case syntax, simple expressions
const x = 3
case (x) {
  (3) { echo three }
  (4) { echo four }
}
## status: 0
## STDOUT:
three
## END

#### case syntax, complex expressions
const x = 3
case (x) {
  (1 + 2) { echo three }
  (2 + 2) { echo four }
}
## STDOUT:
three
## END

#### case semantics, no match
const x = 2
case (x) {
  (3) { echo three }
  (4) { echo four }
}
## status: 0
## STDOUT:
## END

#### case syntax, eggex
const x = "main.cc"
case (x) {
  / dot* '.py' / {
    echo Python
  }
  / dot* ('.cc' | '.h') / {
   echo C++
  }
}
## STDOUT:
## END

#### empty case statement
const x = ""
case (x) { }
## status: 0
## STDOUT:
## END

#### typed args
const x = "0"
case (x) {
  (0) { echo int }
  ("0") { echo string }
}

# FIXME: stdout should be "string", but right now it is "int"

## status: 0
## STDOUT:
string
## END

#### old and new case statements

for flag in -f -x {

  # We can disallow this with shopt --unset parse_old_case, because the new
  # case statement does everything the old one does
  #
  # bin/osh and shopt --set ysh:upgrade let you use both styles, but bin/ysh
  # only lets you use the new style

  case $flag in
    -f|-d)
      echo 'file'
      ;;
    *)
      echo 'other'
      ;;
  esac

  case (flag) {
    -f|-d { echo 'file' }
    *     { echo 'other' }
  }

  echo --
}

## STDOUT:
file
file
--
other
other
--
## END
