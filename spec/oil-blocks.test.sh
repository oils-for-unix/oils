# Oil Blocks


#### cd with block
shopt -s oil:all
# OLDPWD is NOT defined
cd / { echo $PWD; echo OLDPWD=${OLDPWD:-} }; echo done
echo $(basename $PWD)  # restored
cd /tmp {
  write PWD=$PWD
  write -sep ' ' pwd builtin: $(pwd)
}
echo $(basename $PWD)  # restored
## STDOUT:
/
OLDPWD=
done
oil-blocks.test.sh
PWD=/tmp
pwd builtin: /tmp
oil-blocks.test.sh
## END

#### cd with block: fatal error in block
shopt -s oil:all
cd / {
  echo one
  false
  echo two
}
## status: 1
## STDOUT:
one
## END


#### cd with block: return in block
shopt -s oil:all
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

#### cd with block: break in block
shopt -s oil:all
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

#### cd with block exits with status 0
shopt -s oil:all
cd / {
  echo block

  # This return value is ignored.
  # Or maybe this should be a runtime error?
  return 1
}
echo status=$?
## STDOUT:
block
status=0
## END

#### block has its own scope, e.g. shadows outer vars
shopt -s oil:all
var x = 1
cd / {
  #set y = 5  # This would be an error because set doesn't do dynamic lookup
  var x = 42
  echo "inner x = $x"
}
echo "outer x = $x"
## STDOUT:
inner x = 42
outer x = 1
## END


