#### OSH behavior
x=1
echo status=$?
echo x=$x

y = 2
echo status=$?
echo y=$y
## STDOUT:
status=0
x=1
status=127
y=
## END

#### ysh:upgrade behavior
shopt --set ysh:upgrade

# allow errors
set +o errexit +o nounset

x=1
echo status=$?
echo x=$x

y = 2
echo status=$?
echo y=$y
## status: 2
## STDOUT:
status=0
x=1
## END

#### ysh:all disallows x=y inside functions, but allows it at the top level
shopt --set ysh:all

# allow errors
set +o errexit +o nounset

x=1  # fails here
echo status=$?
echo x=$x

y = 2
echo status=$?
echo y=$y
## status: 2
## STDOUT:
## END


#### parse_equals: allows bare assignment in Caps blocks
shopt --set parse_proc parse_brace parse_equals 

proc Rule {
  true
}

Rule {
  x = 1 + 2*3
}
echo x=$x

# still allowed since we didn't unset parse_sh_assign
y=foo
echo y=$y

## STDOUT:
x=
y=foo
## END

#### bare assignment inside Hay blocks

shopt --set ysh:all

hay define Package

# problem: we would allow it here, which is weird

proc p { 
  var x = 42
}

cd /tmp {
  var x = 'hi'
}

hay eval :result {
  Package {
    version = 1
  }
}

var x = 1
echo "x is $x"

## STDOUT:
x is 1
## END


