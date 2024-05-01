# Pretty printing tests

#### Int
=  -123
## stdout: (Int)   -123

#### Float
= -0.00
## stdout: (Float)   -0.0

#### Null
= null
## stdout: (Null)   null

#### Bool
=       true
=       false
## STDOUT:
(Bool)   true
(Bool)   false
## END

#### String
= "double quoted"  
= 'single quoted'
## STDOUT:
(Str)   "double quoted"
(Str)   "single quoted"
## END

#### Bash Array
declare -a array_0=()
declare -a array_1=(hello)
declare -a array_3
array_3[0]="world"
array_3[2]=*.py
declare array_long=(Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed
do eiusmod.)
= array_0
= array_1
= array_3
= array_long
## STDOUT:
(BashArray)   (BashArray)
(BashArray)   (BashArray "hello")
(BashArray)   (BashArray "world" null "*.py")
(BashArray)
(BashArray
    "Lorem"
    "ipsum"
    "dolor"
    "sit"
    "amet,"
    "consectetur"
    "adipiscing"
    "elit,"
    "sed"
    "do"
    "eiusmod."
)
## END

#### Bash Assoc
declare -A assoc_0=()
declare -A assoc_1=([1]=one)
declare assoc_3=([1]=one [two]=2 [3]=three)
declare assoc_long=([Lorem]=ipsum [dolor]="sit amet," ['consectetur adipiscing']="elit, sed" [do]="eiusmod.")
= assoc_0
= assoc_1
= assoc_3
= assoc_long
## STDOUT:
(BashAssoc)   (BashAssoc)
(BashAssoc)   (BashAssoc ["1"]="one")
(BashAssoc)   (BashAssoc ["1"]="one" ["two"]="2" ["3"]="three")
(BashAssoc)
(BashAssoc
    ["Lorem"]="ipsum"
    ["dolor"]="sit amet,"
    ["consectetur adipiscing"]="elit, sed"
    ["do"]="eiusmod."
)
## END
