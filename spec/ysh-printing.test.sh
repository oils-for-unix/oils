# Pretty printing tests

#### Int
=  -123
## STDOUT:
(Int)   -123
## END

#### Float
= -0.00
## STDOUT:
(Float) -0.0
## END

#### Null
= null
## STDOUT:
(Null)  null
## END

#### Bool
=       true
=       false
## STDOUT:
(Bool)  true
(Bool)  false
## END

#### String
= "double quoted"
= 'single quoted'
## STDOUT:
(Str)   'double quoted'
(Str)   'single quoted'
## END

#### Range
var x = 1..100

pp value (x)

# TODO: show type here, like (Range 1 .. 100)

pp value ({k: x})

echo

remove-addr() {
  sed 's/0x[0-9a-f]\+/0x---/'
}

pp line (x) | remove-addr
pp line ({k: x}) | remove-addr

## STDOUT:
(Range 1 .. 100)
(Dict)  {k: (Range 1 .. 100)}

<Range 0x--->
(Dict)   {"k":<Range 0x--->}
## END


#### Eggex (reference type)
var pat = /d+/

remove-addr() {
  sed 's/0x[0-9a-f]\+/0x---/'
}

pp value (pat) | remove-addr

pp value ({k: pat}) | remove-addr

# TODO: change this

echo

pp line (pat) | remove-addr
pp line ({k: pat}) | remove-addr

## STDOUT:
<Eggex 0x--->
(Dict)  {k: <Eggex 0x--->}

<Eggex 0x--->
(Dict)   {"k":<Eggex 0x--->}
## END

#### SparseArray, new representation for bash array
declare -a empty=()
declare -a array_1=(hello)
array_1[5]=5

var empty = _a2sp(empty)
var array_1 = _a2sp(array_1)

pp value (empty)
pp value (array_1)
echo

pp value ({k: empty})
pp value ({k: array_1})
echo

pp line (empty)
pp line (array_1)
echo

pp line ({k: empty})
pp line ({k: array_1})

## STDOUT:
(SparseArray)
(SparseArray [0]='hello' [5]='5')

(Dict)  {k: (SparseArray)}
(Dict)  {k: (SparseArray [0]='hello' [5]='5')}

{"type":"SparseArray","data":{}}
{"type":"SparseArray","data":{"0":"hello","5":"5"}}

(Dict)   {"k":{"type":"SparseArray","data":{}}}
(Dict)   {"k":{"type":"SparseArray","data":{"0":"hello","5":"5"}}}
## END

#### BashArray, short
declare -a empty=()
declare -a array_1=(hello)

pp value (empty)
pp value (array_1)
echo

pp value ({k: empty})
pp value ({k: array_1})
echo

pp line (empty)
pp line (array_1)
echo

pp line ({k: empty})
pp line ({k: array_1})

## STDOUT:
(BashArray)
(BashArray 'hello')

(Dict)  {k: (BashArray)}
(Dict)  {k: (BashArray 'hello')}

{"type":"BashArray","data":{}}
{"type":"BashArray","data":{"0":"hello"}}

(Dict)   {"k":{"type":"BashArray","data":{}}}
(Dict)   {"k":{"type":"BashArray","data":{"0":"hello"}}}
## END

#### BashArray, long
declare -a array_3
array_3[0]="world"
array_3[2]=*.py
declare array_long=(Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed
do eiusmod.)
= array_3
= array_long
## STDOUT:
(BashArray 'world' null '*.py')
(BashArray
    'Lorem'       'ipsum'       'dolor'       'sit'         'amet,'
    'consectetur' 'adipiscing'  'elit,'       'sed'         'do'
    'eiusmod.'
)
## END

#### BashAssoc, short
declare -A empty
declare -A assoc=(['k']=$'foo \x01\u03bc')

pp value (empty)
pp value (assoc)
echo

pp value ({k:empty})
pp value ({k:assoc})
echo

pp line (empty)
pp line (assoc)
echo

pp line ({k:empty})
pp line ({k:assoc})

## STDOUT:
(BashAssoc)
(BashAssoc ['k']=$'foo \u0001μ')

(Dict)  {k: (BashAssoc)}
(Dict)  {k: (BashAssoc ['k']=$'foo \u0001μ')}

{"type":"BashAssoc","data":{}}
{"type":"BashAssoc","data":{"k":"foo \u0001μ"}}

(Dict)   {"k":{"type":"BashAssoc","data":{}}}
(Dict)   {"k":{"type":"BashAssoc","data":{"k":"foo \u0001μ"}}}
## END


#### BashAssoc, long
declare -A assoc_0=()
declare -A assoc_1=([1]=one)
declare assoc_3=([1]=one [two]=2 [3]=three)
declare assoc_long=([Lorem]=ipsum [dolor]="sit amet," ['consectetur adipiscing']="elit, sed" [do]="eiusmod.")
= assoc_0
= assoc_1
= assoc_3
= assoc_long
## STDOUT:
(BashAssoc)
(BashAssoc ['1']='one')
(BashAssoc ['1']='one' ['two']='2' ['3']='three')
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
(List)  ['one', 'two', [...]]
(Dict)  {dead_end: null, live_end: {...}}
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
