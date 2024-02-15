# Called from spec/ysh-builtins.test.sh

shopt -s ysh:upgrade  # TODO: bad proc error message without this!

# Set up a file
seq 3 > tmp.txt

proc read-lines (; out) {
  var lines = []
  while read --line {
    append $_reply (lines)

    # Can also be:
    # call lines->append(_reply)
    # call lines->push(_reply)  # might reame it
  }
  call out->setValue(lines)
}

var x
read-lines (&x) < tmp.txt
json write (x)

