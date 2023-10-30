## our_shell: ysh
## oils_failures_allowed: 3

#### Local place

func fillPlace(place) {
  echo zzz | read (place)
}

proc p {
  var x = 'hi'
  :: fillPlace(&x)
  echo "p x=$x"
}

x=global

p

echo "global x=$x"


## STDOUT:
p x=zzz
global x=global
## END


#### Places can't dangle; they should be passed UP the stakc only

func f() {
  var f_local = null
  return (&f_local)
}

func g() {
  # This place is now INVALID!
  var place = f()

  # Should fail when we try to use the place
  echo zzz | read (&place)

  # This should also fail
  :: place->setValue('zzz')
}

:: g()

## STDOUT:
## END


#### Container Place (Dict)

var d = {key: 'hi'}

echo zzz | read --all (&d.key)

# I guess this works
echo newkey | read --all (&d.newkey)

echo key=$[d.key]
echo key=$[d.newkey]

## STDOUT:
## END


