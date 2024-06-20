# spec/ysh-builtin-error

## our_shell: ysh
## oils_failures_allowed: 0

#### try expects an argument

try
echo status=$?

## status: 3
## STDOUT:
## END

#### User errors behave like builtin errors
func divide(a, b) {
  if (b === 0) {
    error 'divide by zero' (code=3)
  }

  return (a / b)
}

# errors can be caught with try
try { = divide(42, 0) }
echo status=$_status

= divide(42, 0)  # sets status to 3
## status: 3
## STDOUT:
status=3
## END

#### _error register is initially empty dict

echo $[type(_error)]
echo $[len(_error)]

## STDOUT:
Dict
0
## END

#### Error sets _error.message, which can be used by programs

func divide(a, b) {
  if (b === 0) {
    error "divide by zero: $a / $b" (code=3)
  }
  return (a / b)
}

try { = divide(42, 0) }
echo status=$_status
echo message=$[_error.message]

proc p {
  echo $[divide(5, 0)]
}

try { p }
echo status=$_status
echo message=$[_error.message]

# Design bug: this isn't caught!

# try echo $[divide(3, 0]

## STDOUT:
status=3
message=divide by zero: 42 / 0
status=3
message=divide by zero: 5 / 0
## END

#### error builtin adds named args as properties on _error Dict

try {
  error 'bad' (code=99)
}
pp line (_error)

# Note: myData co
try {
  error 'bad' (code=99, myData={spam:'eggs'})
}
pp line (_error)

try {
  error 'bad' (code=99, message='cannot override')
}
pp line (_error)

## STDOUT:
(Dict)   {"code":99,"message":"bad"}
(Dict)   {"myData":{"spam":"eggs"},"code":99,"message":"bad"}
(Dict)   {"message":"bad","code":99}
## END

#### Errors within multiple functions
func inverse(x) {
  if (x === 0) {
    error '0 does not have an inverse'  # default status is 1
  }

  return (1 / x)
}

func invertList(list) {
  var result = []
  for item in (list) {
    call result->append(inverse(item))
  }
  return (result)
}

= invertList([1, 2, 0])
## status: 10
## STDOUT:
## END

#### Impact of errors on var declaration
func alwaysError() {
  error "it's an error" (status=100)
}

try {
  var mylist = [1 + 2, alwaysError()]

  echo this will never be printed
}
= mylist  # undefined! status becomes 1
## status: 1
## STDOUT:
## END

#### Error defaults status to 10
error 'some error'
## status: 10
## STDOUT:
## END

#### error expects an integer code
error 'error' (code='a string?')
## status: 3
## STDOUT:
## END

#### Error typed arg, not named arg
error msg (100)
## status: 3
## STDOUT:
## END

#### Errors cannot take command args
error uh-oh ('error', status=1)
## status: 3
## STDOUT:
## END

#### Error must take arguments
error
## status: 2
## STDOUT:
## END

#### Errors cannot have a status of 0
error ('error', status=0)
## status: 2
## STDOUT:
## END

#### try { error oops }

try { error oops }
echo status=$_status

## STDOUT:
status=10
## END
