## compare_shells: bash
## oils_failures_allowed: 1

#### invoke usage
case $SH in bash) exit ;; esac

invoke
echo status=$?

invoke --
echo status=$?

invoke sleep 0
echo status=$?

invoke -- sleep 0
echo status=$?

## STDOUT:
status=2
status=2
status=1
status=1
## END
## N-I bash STDOUT:
## END


#### cat
case $SH in bash) exit ;; esac

enable --internal cat

# invoke --internal cat
# invoke -i cat

seq 3 | __cat

## STDOUT:
1
2
3
## END
## N-I bash STDOUT:
## END

#### sleep

enable --internal sleep

sleep -1
echo status=$?

sleep -- -1
echo status=$?

sleep 0
echo status=$?

sleep -- 0
echo status=$?

sleep 0.005
echo status=$?

sleep '+0.005'
echo status=$?

sleep '+0.005s'
echo status=$?

## STDOUT:
status=1
status=1
status=0
status=0
status=0
status=0
status=0
## END

#### readlink
case $SH in bash) exit ;; esac

echo TODO

# turn this into a builtin
# does that mean any builtin can be externalized?
# - [ aka test is a good candiate
# - we have stubs from true/false

## STDOUT:
## END

## N-I bash STDOUT:
## END
