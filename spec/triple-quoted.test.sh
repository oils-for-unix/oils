
#### Double Quoted

two=2
three=3

echo """
  one
  two = $two
  three = $three
  """

shopt --set parse_triple_quoted

# Now this should be dedented, and I think the first newline doens't count?

echo """
  one
  two = $two
  three = $three
  """

## STDOUT:

  one
  two = 2
  three = 3
  
one
two = 2
three = 3
## END
   

#### more

echo '''
  one
  two = $two
  three = $three
  '''

## STDOUT:

  one
  two = $two
  three = $three
  
## END

#### here doc with quotes

# This has 3 right double quotes

cat <<EOF
"hello"
""
"""
EOF


## STDOUT:
"hello"
""
"""
## END


