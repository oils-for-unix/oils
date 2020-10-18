
#### run builtin
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
    run myproc || echo "failed"
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

#### run with !
shopt -s oil:all || true

deploy() {
  echo 'one'
  false
  echo 'two'
}

#if ! deploy; then
#  echo 'failed'
#fi

if ! run deploy; then
  echo 'failed'
fi
echo done

## STDOUT:
one
failed
done
## END

#### run -bool-status with external command

set -o errexit

echo hi > file.txt

if run --bool-status -- grep pat file.txt; then
  echo 'match'
else 
  echo 'no match'
fi

if run --bool-status -- grep pat BAD; then
  echo 'match'
else 
  echo 'no match'
fi

echo DONE
## status: 2
## STDOUT:
no match
## END

#### run -bool-status with function

set -o errexit

echo hi > file.txt

myproc() {
  echo ---
  grep pat BAD  # exits with code 2
  #grep pat file.txt
  echo ---
}

#myproc

if run --bool-status -- myproc; then
  echo 'match'
else 
  echo 'no match'
fi

## status: 2
## STDOUT:
---
## END

#### run syntax error
set -o errexit

# Irony: we can't fail that hard here because errexit is disabled before
# we enable it.
# TODO: We could special case this perhaps

if run; then
  echo hi
else
  echo fail
fi

## status: 2
## STDOUT:
## END

#### run --assign-status
set -o errexit

myproc() {
  return 42
}

run --assign-status st -- myproc
echo st=$st

# colon
run --assign-status :st -- myproc
echo st=$st


## STDOUT:
st=42
st=42
## END
