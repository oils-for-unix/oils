#### _status

shopt --unset errexit {

  ( exit 3 )
  echo status=$_status

  ( exit 4 )

  var st = $_status
  echo st=$st
}

## STDOUT:
status=3
st=4
## END
