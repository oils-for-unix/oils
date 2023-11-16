
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

#### promptVal() with invalid char

var x = _io->promptVal('ZZ')
echo x=$x

## STDOUT:
x=<Error: \ZZ not implemented in $PS1>
## END

