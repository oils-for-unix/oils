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
