
#### ${#s} and len(s)

source $REPO_ROOT/spec/testdata/unicode.sh

# bash agrees
echo "farmer scalars =" ${#farmer}

echo "facepalm scalars =" ${#facepalm}

echo "farmer len =" $[len(farmer)]

echo "facepalm len =" $[len(facepalm)]

## STDOUT:
farmer scalars = 4
facepalm scalars = 5
farmer len = 15
facepalm len = 17
## END
