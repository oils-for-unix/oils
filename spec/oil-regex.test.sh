# Test out Oil's regular expression syntax.

#### /./
shopt -s all:oil
if ('' ~ /./) {  # ERE syntax
  echo yes
} else {
  echo no
}
if ('f' ~ /./) {  # ERE syntax
  echo yes
} else {
  echo no
}

## STDOUT:
no
yes
## END


#### /.+/
shopt -s all:oil

var s = 'foo'
if (s ~ /.+/) {  # ERE syntax
  echo no
}
var empty = ''
if (empty ~ /.+/) {
  echo yes
} else {
  echo no
}
## STDOUT:
yes
no
## END
