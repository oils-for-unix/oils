## oils_failures_allowed: 1

#### echo `cat OSCFLAGS` "world" > OSCFLAGS (from Alpine imap)

echo hello > OSCFLAGS
#strace --follow-forks --trace=openat $0 -c 'echo `cat OSCFLAGS` "world" > OSCFLAGS'
echo `cat OSCFLAGS` "world" > OSCFLAGS
#echo $(cat OSCFLAGS) "world" > OSCFLAGS
cat OSCFLAGS

## STDOUT:
hello world
## END

#### 2 echo `cat OSCFLAGS` "world" > OSCFLAGS (from Alpine imap)

echo hello > OSCFLAGS
(echo `cat OSCFLAGS` "world") > OSCFLAGS
cat OSCFLAGS

echo hello > OSCFLAGS
for x in 1 2 3; do echo `cat OSCFLAGS` "world"; done > OSCFLAGS
cat OSCFLAGS

## STDOUT:
world
world
world world
world world world world
## END

#### for word + redirect order

echo hello > OSCFLAGS
for x in `cat OSCFLAGS` world; do
  echo $x
done > OSCFLAGS
cat OSCFLAGS

## STDOUT:
world
## END

#### case word + redirect order

echo hello > OSCFLAGS
case `cat OSCFLAGS` in
  hello)
    echo hello
    ;;
  *)
    echo other
    ;;
esac > OSCFLAGS
cat OSCFLAGS

## STDOUT:
other
## END

#### [[ + redirect order
case $SH in dash|ash) exit ;; esac

echo hello > OSCFLAGS

[[ `cat OSCFLAGS` = hello ]] > OSCFLAGS
echo status=$?

# it is the empty string!
[[ `cat OSCFLAGS` = '' ]] > OSCFLAGS
echo status=$?

## STDOUT:
status=1
status=0
## END

## N-I dash/ash STDOUT:
## END
