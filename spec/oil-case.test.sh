# spec/oil-case

#### case syntax, oneline
const x = "header.h"
case (x) {
  *.h | *.cc { echo C++ }
  *.py       { echo Python }
}
## status: 0
## STDOUT:
C++
## END

#### case syntax, multiline
const x = "hello.py"
case (x) {
  *.h | *.cc {
    echo C++
  }
  *.py {
    echo Python
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
## status: 2
## STDOUT:
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
## status: 2
## STDOUT:
## END

#### empty case statement
const x = ""
case (x) { }
## status: 0
## STDOUT:
## END
