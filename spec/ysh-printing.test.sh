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

#### Range
var x = 1..100
= x
## stdout: (Range)   1 .. 100

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
(BashArray)   (BashArray 'hello')
(BashArray)   (BashArray 'world' null '*.py')
(BashArray)
(BashArray
    'Lorem'       'ipsum'       'dolor'       'sit'         'amet,'
    'consectetur' 'adipiscing'  'elit,'       'sed'         'do'
    'eiusmod.'
)
## END

#### Bash Assoc: string formatting
declare -A assoc=(['k']=$'foo \x01\u03bc')
= assoc
## stdout: (BashAssoc)   (BashAssoc ['k']=$'foo \u0001μ')

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
(BashAssoc)   (BashAssoc ['1']='one')
(BashAssoc)   (BashAssoc ['1']='one' ['two']='2' ['3']='three')
(BashAssoc)
(BashAssoc
    ['Lorem']='ipsum'
    ['dolor']='sit amet,'
    ['consectetur adipiscing']='elit, sed'
    ['do']='eiusmod.'
)
## END

#### Simple Cycles
var cyclic_array = ["one", "two", "three"]
setvar cyclic_array[2] = cyclic_array
var cyclic_dict = {"dead_end": null}
setvar cyclic_dict["live_end"] = cyclic_dict
= cyclic_array
= cyclic_dict
## STDOUT:
(List)   ["one", "two", [...]]
(Dict)   {dead_end: null, live_end: {...}}
## END

#### Complex Cycles
var dict = {}
setvar dict["nothing"] = null
var simple_cycle = [["dummy"]]
setvar simple_cycle[0][0] = simple_cycle
setvar dict["simple_cycle"] = simple_cycle
var tricky_cycle = ["dummy"]
setvar tricky_cycle[0] = dict
setvar dict["tricky_cycle"] = tricky_cycle
var dag = [1, 2, "dummy"]
setvar dag[2] = dag
setvar dict["dag"] = [dag, dag]
var alpha = {}
var omega = {}
setvar alpha["omega"] = omega
setvar omega["alpha"] = alpha
setvar dict["key_alpha"] = alpha
setvar dict["key_omega"] = omega
= dict
## STDOUT:
(Dict)
{
    nothing: null,
    simple_cycle: [[[...]]],
    tricky_cycle: [{...}],
    dag: [[1, 2, [...]], [1, 2, [...]]],
    key_alpha: {omega: {alpha: {...}}},
    key_omega: {alpha: {omega: {...}}}
}
## END
