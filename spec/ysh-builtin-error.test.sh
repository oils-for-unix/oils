# spec/ysh-builtin-error

## our_shell: ysh
## oils_failures_allowed: 1

#### User errors behave like builtin errors
func divide(a, b) {
  if (b === 0) {
    error ('divide by zero', status=3)
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

#### Error messages can be read in userspace
func divide(a, b) {
  if (b === 0) {
    error ('divide by zero', status=3)
  }

  return (a / b)
}

try { = divide(42, 0) }
echo status=$_status
echo message=$_error_message
## STDOUT:
status=3
message=divide by zero
## END

#### Errors within multiple functions
func inverse(x) {
  if (x === 0) {
    error ('0 does not have an inverse')  # default status is 1
  }

  return (1 / x)
}

func invertList(list) {
  var result = []
  for item in (list) {
    _ result->append(inverse(item))
  }
  return (result)
}

= invertList([1, 2, 0])
## status: 1
## STDOUT:
## END

#### Impact of errors on var declaration
func alwaysError() {
  error ("it's an error", status=100)
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
error ('some error')
## status: 1
## STDOUT:
## END

#### Error expects a positional argument
error (status=42)
## status: 3
## STDOUT:
## END

#### Error will object to an incorrect named arg
error ('error', status_typo=42)
## status: 3
## STDOUT:
## END

#### Error will object to an extraneous named arg
error ('error', status=42, other=100)
## status: 3
## STDOUT:
## END

#### Error expects an int status
error ('error', status='a string?')
## status: 3
## STDOUT:
## END

#### Error expects a string message
error (100, status=42)
## status: 3
## STDOUT:
## END

#### Errors cannot take command args
error uh-oh ('error', status=1)
## status: 2
## STDOUT:
## END

#### Error must take arguments
error
## status: 3
## STDOUT:
## END

#### Errors cannot have a status of 0
error ('error', status=0)
## status: 1
## STDOUT:
## END
