## our_shell: ysh
## oils_failures_allowed: 1

#### Local place

func f(place) {
  var x = 'f'
  echo zzz | read --line (place)
  echo "f x=$x"
}

func fillPlace(place) {
  var x = 'fillPlace'
  :: f(place)
  echo "fillPlace x=$x"
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
f x=f
fillPlace x=fillPlace
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
  echo zzz | read --line (place)

  # This should also fail
  # :: place->setValue('zzz')

}

:: g()

echo done

## status: 1
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


