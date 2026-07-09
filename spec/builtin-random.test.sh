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

$SH -c 'RANDOM=seed; echo $RANDOM $RANDOM' > one.txt
$SH -c 'RANDOM=seed; echo $RANDOM $RANDOM' > two.txt
diff -u one.txt two.txt
echo diff=$?

## STDOUT:
diff=0
## END
## BUG mksh STDOUT:
## END

#### unset RANDOM resets its special function

unset RANDOM
[[ -z $RANDOM ]] && echo empty

## STDOUT:
empty
## END
