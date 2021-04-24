
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

#### run -allow-status-01 with external command

set -o errexit

echo hi > file.txt

if run --allow-status-01 -- grep pat file.txt; then
  echo 'match'
else 
  echo 'no match'
fi

if run --allow-status-01 -- grep pat BAD; then
  echo 'match'
else 
  echo 'no match'
fi

echo DONE
## status: 2
## STDOUT:
no match
## END

#### run -allow-status-01 with function

set -o errexit

echo hi > file.txt

myproc() {
  echo ---
  grep pat BAD  # exits with code 2
  #grep pat file.txt
  echo ---
}

#myproc

if run --allow-status-01 -- myproc; then
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


#### run --status-ok SIGPIPE

yes | head -n 1
echo pipeline=${_pipeline_status[@]}

run --status-ok SIGPIPE -- yes | head -n 1
echo pipeline=${_pipeline_status[@]}

set -o errexit

if run --status-ok SIGPIPE -- yes | head -n 1; then
  echo OK
  echo pipeline=${_pipeline_status[@]}
fi


## STDOUT:
y
pipeline=141 0
y
pipeline=0 0
y
OK
pipeline=0 0
## END

#### run --status-ok SIGPIPE with builtin printf

bad() {
  /usr/bin/printf '%65538s\n' foo | head -c 1
  echo external ${_pipeline_status[@]}

  run --status-ok SIGPIPE /usr/bin/printf '%65538s\n' foo | head -c 1
  echo external supressed ${_pipeline_status[@]}

  printf '%65538s\n' foo | head -c 1
  echo builtin ${_pipeline_status[@]}

  run --status-ok SIGPIPE printf '%65538s\n' foo | head -c 1
  echo builtin suppressed ${_pipeline_status[@]}
}

bad
echo finished

## STDOUT:
 external 141 0
 external suppressed  0 0
 builtin 141 0
 builtin suppressed  0 0
finished
## END

#### run --push-status (preserves last exit code)
f42() {
  return 42
}
f42
echo bare status=$?

run --push-status -- f42
echo run status=$?
## STDOUT:
bare status=42
run status=0
## END

#### run --push-status --assign-status (preserves last exit code and assigns inner one)

f42() {
  return 42
}
f42
echo bare status=$?

run --assign-status :st -- f42
echo run status=$? st=$st

( exit 43 )  # $? is now 43

run --push-status --assign-status :st -- f42
echo after push status=$? st=$st

## STDOUT:
bare status=42
run status=0 st=42
after push status=43 st=42
## END
