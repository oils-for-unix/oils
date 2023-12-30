# spec/ysh-builtin-error

## our_shell: ysh
## oils_failures_allowed: 1

#### User errors behave like builtin errors
func divide(a, b) {
  if (b === 0) {
    error 'divide by zero' (status=3)
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

#### Error sets _error_message, which can be used by programs

func divide(a, b) {
  if (b === 0) {
    error 'divide by zero' (status=3)
  }
  return (a / b)
}

try { = divide(42, 0) }
echo status=$_status
echo message=$[_error.message]

## STDOUT:
status=3
message=divide by zero
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
## status: 1
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

#### Error defaults status to 1
error 'some error'
## status: 1
## STDOUT:
## END

#### Error will object to an incorrect named arg
error 'error' (status_typo=42)
## status: 3
## STDOUT:
## END

#### Error will object to an extraneous named arg
error 'error' (status=42, other=100)
## status: 3
## STDOUT:
## END

#### Error expects an int status
error 'error' (status='a string?')
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

#### Two styles of try with error builtin behave the same way (bug)

try { error oops }
echo status=$_status

try error oops
echo status=$_status

## STDOUT:
status=1
status=1
## END
