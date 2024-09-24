

#### cd builtin: fatal error in block
shopt -s ysh:all
cd / {
  echo one
  false
  echo two
}
## status: 1
## STDOUT:
one
## END


#### cd builtin: return in block
shopt -s ysh:all
f() {
  cd / {
    echo one
    return
    echo two
  }
  echo 'end func'
}
f
## STDOUT:
one
end func
## END

#### cd builtin: break in block
shopt -s ysh:all
f() {
  cd / {
    echo one
    for i in 1 2; do
      echo $i
      break  # break out of loop
    done

    break  # break out of block isn't valid
    echo two
  }
  echo end func
}
f
## status: 1
## STDOUT:
one
1
## END

#### proc eval block: fatal error
shopt -s ysh:all

proc proc-that-runs-block (; ; ; b) {
  eval (b)
}
proc-that-runs-block {
  echo one
  false
  echo two
}
## status: 1
## STDOUT:
one
## END

#### proc eval block: return
shopt -s ysh:all

proc proc-that-runs-block (; ; ; b) {
  eval (b)
}

f() {
  proc-that-runs-block {
    echo one
    return
    echo two
  }
  echo 'end func'
}
f
## STDOUT:
one
end func
## END

#### proc eval block: break in block
shopt -s ysh:all

proc proc-that-runs-block (; ; ; b) {
  eval (b)
}

f() {
  proc-that-runs-block {
    echo one
    for i in 1 2; do
      echo $i
      break  # break out of loop
    done

    break  # break out of block isn't valid
    echo two
  }
  echo end func
}
f
## status: 1
## STDOUT:
one
1
## END

#### proc eval string: fatal error
shopt -s ysh:all

proc proc-that-evals (s) {
  eval $s
}
proc-that-evals '
  echo one
  false
  echo two
'
## status: 1
## STDOUT:
one
## END

#### proc eval string: return
shopt -s ysh:all

proc proc-that-evals (s) {
  eval $s
}

f() {
  proc-that-evals '
    echo one
    return
    echo two
  '
  echo 'end func'
}
f
## STDOUT:
one
end func
## END

#### proc eval string: break
shopt -s ysh:all

proc proc-that-evals (s) {
  eval $s
}

f() {
  proc-that-evals '
    echo one
    for i in 1 2; do
      echo $i
      break  # break out of loop
    done

    break  # break out of string is not valid
    echo two
  '
  echo end func
}
f
## status: 1
## STDOUT:
one
1
## END
