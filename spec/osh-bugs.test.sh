# For OSH only functionality

#### var x = $(echo bad; false) in OSH

#shopt -s verbose_errexit

# This turns on command_sub_errexit and fails
var x = $(echo bad; false)
echo 'unreachable'

pp test_ (x)

## status: 1
## STDOUT:
## END


#### var x = $(echo one; false; echo two) in OSH

#shopt -s verbose_errexit

# I don't understand why this doesn't fail
var x = $(echo one; false; echo two)
echo 'unreachable'

pp test_ (x)

## status: 1
## STDOUT:
## END

