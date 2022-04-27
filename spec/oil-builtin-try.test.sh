
#### try builtin
shopt --set errexit strict_errexit

myproc() {
  echo hi
  false
  echo bye
}

case $SH in
  (*osh)
    # new semantics: the function aborts at 'false', the 'catch' builtin exits
    # with code 1, and we echo 'failed'
    try myproc || echo "failed"
    ;;
  (*)
    myproc || echo "failed"
    ;;
esac

## STDOUT:
hi
failed
## END
## N-I dash/bash/mksh/ash STDOUT:
hi
bye
## END

#### try with !
shopt -s oil:all || true

deploy() {
  echo 'one'
  false
  echo 'two'
}

#if ! deploy; then
#  echo 'failed'
#fi

if ! try deploy; then
  echo 'failed'
fi
echo done

## STDOUT:
one
failed
done
## END

#### try syntax error
set -o errexit

# Irony: we can't fail that hard here because errexit is disabled before
# we enable it.
# TODO: We could special case this perhaps

if try; then
  echo hi
else
  echo fail
fi

## status: 2
## STDOUT:
## END

#### try --assign
set -o errexit

myproc() {
  return 42
}

try --assign st -- myproc
echo st=$st

# colon
try --assign :st -- myproc
echo st=$st


## STDOUT:
st=42
st=42
## END

#### boolstatus with external command

set -o errexit

echo hi > file.txt

if boolstatus grep pat file.txt; then
  echo 'match'
else 
  echo 'no match'
fi

# file doesn't exist
if boolstatus grep pat BAD; then
  echo 'match'
else 
  echo 'no match'
fi

echo DONE
## status: 2
## STDOUT:
no match
## END

#### boolstatus disallows procs with strict_errexit
set -o errexit
shopt -s strict_errexit

echo hi > file.txt

not-found() {
  echo not-found
  grep pat file.txt
  echo not-found
}

bad() {
  echo bad
  grep pat BAD  # exits with code 2
  echo bad
}

if boolstatus not-found; then
  echo 'match'
else 
  echo 'no match'
fi

if boolstatus bad; then
  echo 'match'
else 
  echo 'no match'
fi

## status: 1
## STDOUT:
## END

#### boolstatus can call a function without strict_errexit (not recommended)
set -o errexit

echo hi > file.txt

not-found() {
  echo not-found
  grep pat file.txt
  local status=$?
  if test "$status" -ne 0; then
    return $status
  fi
  echo not-found
}

bad() {
  echo bad
  grep pat BAD  # exits with code 2
  local status=$?
  if test "$status" -ne 0; then
    return $status
  fi
  echo bad
}

if boolstatus not-found; then
  echo 'match'
else 
  echo 'no match'
fi

if boolstatus bad; then
  echo 'match'
else 
  echo 'no match'
fi

## status: 2
## STDOUT:
not-found
no match
bad
## END

