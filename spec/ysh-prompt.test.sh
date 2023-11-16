
#### promptVal() with various values

shopt -s ysh:upgrade

var x = _io->promptVal('$')

# We're not root, so it should be $
echo x=$x

var x = _io->promptVal('w')
if (x === PWD) {
  echo pass
} else {
  echo fail
}

## STDOUT:
x=$
pass
## END

#### promptVal() with invalid chars

var x = _io->promptVal('ZZ')
echo x=$x

# \D{} will be supported with date and time functions
var x = _io->promptVal('D')
echo x=$x

## STDOUT:
x=<Error: \ZZ not implemented in $PS1>
x=<Error: \D{} not in promptVal()>
## END

