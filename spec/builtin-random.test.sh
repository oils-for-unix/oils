## oils_failures_allowed: 0
## compare_shells: bash mksh zsh ash

#### $RANDOM produces random numbers
[[ -n $RANDOM ]] && echo set

a=$RANDOM
b=$RANDOM
[[ $a -ne $b ]] && echo random

## STDOUT:
set
random
## END

#### RANDOM=seed seeds a sequence of random numbers

# mksh doesn't implement seeding
case $SH in mksh) exit 0 ;; esac

RANDOM=1
echo $RANDOM
echo $RANDOM

## STDOUT:
## END
## OK ash STDOUT:
9882
31274
## END
## OK zsh STDOUT:
17767
9158
## END
## OK bash STDOUT:
16807
10791
## END
## OK osh STDOUT:
15503
22497
## END
## BUG mksh STDOUT:
## END

#### unset RANDOM resets its special function

unset RANDOM
[[ -z $RANDOM ]] && echo empty

## STDOUT:
empty
## END
