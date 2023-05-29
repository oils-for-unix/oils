#### tuple literal doesn't conflict with ((
if ((0,0) < (0,1)) { echo yes }
## STDOUT:
yes
## END

#### Empty tuple
var t = ()
echo length=$[len(t)]
## STDOUT:
length=0
## END

#### Singleton tuple
var t = tup(42)
echo "length = $[len(t)]"
echo "t[0] = $[t[0]]"

# NOT ALLOWED.  Use tup() instead.
#var t1 = 1,
var t2 = (1,)
## status: 2
## STDOUT:
length = 1
t[0] = 42
## END
