# fork and forkwait

#### fork and forkwait usage  errors
shopt --set oil:basic
shopt --unset errexit

fork
echo status=$?

fork extra
echo status=$?

fork extra {
  echo hi
}
echo status=$?

#

forkwait
echo status=$?

forkwait extra
echo status=$?

forkwait extra {
  echo hi
}
echo status=$?

## STDOUT:
status=2
status=2
status=2
status=2
status=2
status=2
## END

#### forkwait
shopt --set oil:basic
shopt --unset errexit

old=$PWD

forkwait {
  cd /
  echo hi
  exit 42
}
echo status=$?
if test "$old" = "$PWD"; then
  echo ok
fi
## STDOUT:
hi
status=42
ok
## END

#### fork
shopt --set oil:basic
shopt --unset errexit

old=$PWD

fork {
  cd /
  echo hi
  sleep 0.1  # print status first, slightly racy
  exit 42
}
echo status=$?

wait -n
echo status=$?

if test "$old" = "$PWD"; then
  echo ok
fi
## STDOUT:
status=0
hi
status=42
ok
## END
