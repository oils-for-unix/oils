#!/bin/bash

#### tuple comparison
var t1 = 3, 0
var t2 = 4, 0
var t3 = 3, 1

if (t2 > t1) { echo yes1 }
if (t3 > t1) { echo yes2 }
if ( (0,0) > t1) { echo yes3 }

# NOTE: ((0,0)  causes problems -- it looks like a shell statement!
#if ( (0,0) > t1) { echo yes3 }
## STDOUT:
yes1
yes2
## END


#### tuple literal doesn't conflict with ((
if ((0,0) < (0,1)) { echo yes }
## STDOUT:
yes
## END

#### Empty tuple
var t = ()
echo length=$len(t)
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
