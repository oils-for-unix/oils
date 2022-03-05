#### fastlex: NUL byte not allowed inside char literal #' '

echo $'var x = #\'\x00\'; echo x=$x' > tmp.oil
$SH tmp.oil

echo $'var x = #\' ' > incomplete.oil
$SH incomplete.oil

## STDOUT:
## END

#### fastlex: NUL byte inside shebang line

echo $'#! /usr/bin/env \x00 sh \necho hi' > tmp.oil
env OSH_HIJACK_SHEBANG=1 $SH tmp.oil

## STDOUT:
## END
