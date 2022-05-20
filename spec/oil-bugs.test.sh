#### fastlex: NUL byte not allowed inside char literal #' '

echo $'var x = #\'\x00\'; echo x=$x' > tmp.oil
$SH tmp.oil

echo $'var x = #\' ' > incomplete.oil
$SH incomplete.oil

## status: 2
## STDOUT:
## END

#### fastlex: NUL byte inside shebang line

# Hm this test doesn't really tickle the bug

echo $'#! /usr/bin/env \x00 sh \necho hi' > tmp.oil
env OSH_HIJACK_SHEBANG=1 $SH tmp.oil

## STDOUT:
hi
## END

#### Tea keywords don't interfere with Oil expressions

var d = {data: 'foo'}

echo $[d->data]

var e = {enum: 1, class: 2, import: 3, const: 4, var: 5, set: 6}
echo $len(e)

## STDOUT:
foo
6
## END
