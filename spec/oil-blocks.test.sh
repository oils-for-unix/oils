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

#### block doesn't have its own scope
shopt -s oil:all
var x = 1
echo "x=$x"
cd / {
  #set y = 5  # This would be an error because set doesn't do dynamic lookup
  var x = 42
  echo "x=$x"
}
echo "x=$x"
## STDOUT:
x=1
x=42
x=42
## END

#### block literal in expression mode: &(echo $PWD)
shopt -s oil:all

myblock = &(echo $PWD)

b2 = &(echo one; echo two)

# TODO:
# Implement something like this?
# _ evalexpr(b2, binding_dict)  # e.g. to bind to QTSV fields
# _ evalblock(b2, binding_dict)

## STDOUT:
one
two
## END
