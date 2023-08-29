# Hay: Hay Ain't YAML

## oils_failures_allowed: 2

#### use bin
use
echo status=$?
use z
echo status=$?

use bin
echo bin status=$?
use bin sed grep
echo bin status=$?

## STDOUT:
status=2
status=2
bin status=0
bin status=0
## END

#### use dialect
shopt --set parse_brace

use dialect
echo status=$?

use dialect ninja
echo status=$?

shvar _DIALECT=oops {
  use dialect ninja
  echo status=$?
}

shvar _DIALECT=ninja {
  use dialect ninja
  echo status=$?
}

## STDOUT:
status=2
status=1
status=1
status=0
## END

#### hay builtin usage

hay define
echo status=$?

hay define -- package user
echo status=$?

hay pp | wc -l | read n
echo read $?
test $n -gt 0
echo greater $?

## STDOUT:
status=2
status=0
read 0
greater 0
## END

#### hay reset
shopt --set parse_brace

hay define package

hay eval :a {
  package foo
  echo "package $?"
}

hay reset  # no more names

echo "reset $?"

hay eval :b {
  package foo
  echo "package $?"
}

## status: 127
## STDOUT:
package 0
reset 0
## END


#### hay eval can't be nested
shopt --set parse_brace

hay eval :foo {
  echo foo
  hay eval :bar {
    echo bar
  }
}
## status: 127
## STDOUT:
foo
## END

#### hay names at top level
shopt --set parse_brace parse_at
shopt --unset errexit

hay define Package

Package one
echo status=$?

setvar args = _hay()['children'][0]['args']
write --sep ' ' $[len(_hay()['children'])] @args

hay eval :result {
  Package two
  echo status=$?
}

setvar args = result['children'][0]['args']
write --sep ' ' $[len(result['children'])] @args

Package three
echo status=$?

setvar args = _hay()['children'][0]['args']
write --sep ' ' $[len(_hay()['children'])] $[_hay()['children'][0]['args'][0]]

## STDOUT:
status=0
1 one
status=0
1 two
status=0
1 three
## END

#### Parsing Nested Attributes nodes (bug fix)

shopt --set parse_brace parse_equals

hay define Package/License

Package glibc {
  version = '1.0'

  License {
    path = 'LICENSE.txt'
  }

  other = 'foo'
}

json write (_hay()) | jq '.children[0].children[0].attrs' > actual.txt

diff -u - actual.txt <<EOF
{
  "path": "LICENSE.txt"
}
EOF

invalid = 'syntax'  # parse error

## status: 2
## STDOUT:
## END


#### hay eval attr node, and JSON
shopt --set parse_brace parse_equals

hay define Package User

hay eval :result {
  Package foo {
    # not doing floats now
    int = 42
    bool = true
    mynull = null
    mystr = $'spam\n'

    mylist = [5, 'foo', {}]
    # TODO: Dict literals need to be in insertion order!
    #mydict = {alice: 10, bob: 20}
  }

  User alice
}

# Note: using jq to normalize
json write (result) | jq . > out.txt

diff -u - out.txt <<EOF
{
  "source": null,
  "children": [
    {
      "type": "Package",
      "args": [
        "foo"
      ],
      "children": [],
      "attrs": {
        "int": 42,
        "bool": true,
        "mynull": null,
        "mystr": "spam\n",
        "mylist": [
          5,
          "foo",
          {}
        ]
      }
    },
    {
      "type": "User",
      "args": [
        "alice"
      ]
    }
  ]
}
EOF

echo "diff $?"

## STDOUT:
diff 0
## END

#### hay eval shell node, and JSON
shopt --set parse_brace parse_equals

hay define TASK

hay eval :result {
  TASK { echo hi }

  TASK {
    echo one
    echo two
  }
}

#= result
json write (result) | jq . > out.txt

diff -u - out.txt <<'EOF'
{
  "source": null,
  "children": [
    {
      "type": "TASK",
      "args": [],
      "location_str": "[ stdin ]",
      "location_start_line": 6,
      "code_str": "         echo hi "
    },
    {
      "type": "TASK",
      "args": [],
      "location_str": "[ stdin ]",
      "location_start_line": 8,
      "code_str": "        \n    echo one\n    echo two\n  "
    }
  ]
}
EOF

## STDOUT:
## END


#### _hay() register
shopt --set parse_paren parse_brace parse_equals parse_proc

hay define user

var result = {}

hay eval :result {

  user alice
  # = _hay()
  write -- $[len(_hay()['children'])]

  user bob
  setvar result = _hay()
  write -- $[len(_hay()['children'])]

}

# TODO: Should be cleared here
setvar result = _hay()
write -- $[len(_hay()['children'])]

## STDOUT:
1
2
0
## END


#### haynode builtin can define nodes
shopt --set parse_paren parse_brace parse_equals parse_proc

# It prints JSON by default?  What about the code blocks?
# Or should there be a --json flag?

hay eval :result {

  # note that 'const' is required because haynode isn't capitalized
  haynode parent alice {
    const age = '50'
    
    haynode child bob {
      const age = '10'
    }

    haynode child carol {
      const age = '20'
    }

    const other = 'str'
  }
}

#= result
write -- 'level 0 children' $[len(result['children'])]
write -- 'level 1 children' $[len(result['children'][0]['children'])]

hay eval :result {
  haynode parent foo
  haynode parent bar
}
write -- 'level 0 children' $[len(result['children'])]


## STDOUT:
level 0 children
1
level 1 children
2
level 0 children
2
## END


#### haynode: usage errors (name or block required)
shopt --set parse_brace parse_equals parse_proc

# should we make it name or block required?
# license { ... } might be useful?

try {
  hay eval :result {
    haynode package
  }
}
echo "haynode attr $_status"
var result = _hay()
echo "LEN $[len(result['children'])]"

# requires block arg
try {
  hay eval :result {
    haynode TASK build
  }
}
echo "haynode code $_status"
echo "LEN $[len(result['children'])]"

echo ---
hay define package TASK

try {
  hay eval :result {
    package
  }
}
echo "define attr $_status"
echo "LEN $[len(result['children'])]"

try {
  hay eval :result {
    TASK build
  }
}
echo "define code $_status"
echo "LEN $[len(result['children'])]"

## STDOUT:
haynode attr 2
LEN 0
haynode code 2
LEN 0
---
define attr 2
LEN 0
define code 2
LEN 0
## END

#### haynode: shell nodes require block args; attribute nodes don't

shopt --set parse_brace parse_equals parse_proc

hay define package TASK

try {
  hay eval :result {
    package glibc > /dev/null
  }
}
echo "status $_status"


try {
  hay eval :result {
    TASK build
  }
}
echo "status $_status"

## STDOUT:
status 0
status 2
## END


#### hay eval with shopt -s oil:all
shopt --set parse_brace parse_equals parse_proc

hay define Package

const x = 'foo bar'

hay eval :result {
  Package foo {
    # set -e should be active!
    #false

    version = '1.0'

    # simple_word_eval should be active!
    write -- $x
  }
}

## STDOUT:
foo bar
## END


#### Scope of Variables Inside Hay Blocks

shopt --set oil:all

hay define package
hay define deps/package

hay eval :result {

  const URL_PATH = 'downloads/foo.tar.gz'

  package foo {
    echo "location = https://example.com/$URL_PATH"
    echo "backup = https://archive.example.com/$URL_PATH"
  }

  # Note: PushTemp() happens here
  deps spam {
    # OVERRIDE
    const URL_PATH = 'downloads/spam.tar.gz'

    const URL2 = 'downloads/spam.tar.xz'

    package foo {
      # this is a global
      echo "deps location https://example.com/$URL_PATH"
      echo "deps backup https://archive.example.com/$URL2"
    }
  }

  echo "AFTER $URL_PATH"

}

## STDOUT:
location = https://example.com/downloads/foo.tar.gz
backup = https://archive.example.com/downloads/foo.tar.gz
deps location https://example.com/downloads/spam.tar.gz
deps backup https://archive.example.com/downloads/spam.tar.xz
AFTER downloads/foo.tar.gz
## END


#### hay define and then an error
shopt --set parse_brace parse_equals parse_proc

hay define Package/License User TASK

hay pp defs > /dev/null

hay eval :result {
  User bob
  echo "user $?"

  Package cppunit
  echo "package $?"

  TASK build {
    configure
  }
  echo "TASK $?"

  Package unzip {
    version = '1.0'

    License FOO {
      echo 'inside'
    }
    echo "license $?"

    License BAR
    echo "license $?"

    zz foo
    echo 'should not get here'
  }
}

echo 'ditto'

## status: 127
## STDOUT:
user 0
package 0
TASK 0
inside
license 0
license 0
## END

#### parse_hay()
shopt --set parse_proc

const config_path = "$REPO_ROOT/spec/testdata/config/ci.oil"
const block = parse_hay(config_path)

# Are blocks opaque?
{
  = block
} | wc -l | read n

# Just make sure we got more than one line?
if test "$n" -gt 1; then
  echo "OK"
fi

## STDOUT:
OK
## END


#### Code Blocks: parse_hay() then shvar _DIALECT= { eval_hay() }
shopt --set parse_brace parse_proc

hay define TASK

const config_path = "$REPO_ROOT/spec/testdata/config/ci.oil"
const block = parse_hay(config_path)

shvar _DIALECT=sourcehut {
  const d = eval_hay(block)
}

const children = d['children']
write 'level 0 children' $[len(children)] ---

# TODO: Do we need @[] for array expression sub?
write 'child 0' $[children[0].type] $[join(children[0].args)] ---
write 'child 1' $[children[1].type] $[join(children[1].args)] ---

## STDOUT:
level 0 children
2
---
child 0
TASK
cpp
---
child 1
TASK
publish-html
---
## END

#### eval_hay() usage
shopt -s parse_brace

try {
  var d = eval_hay()
}
echo status $_status

try {
  var d = eval_hay(3)
}
echo status $_status

try {
  var d = eval_hay(^(echo hi), 5)
}
echo status $_status

## STDOUT:
status 3
status 3
status 3
## END

#### Attribute / Data Blocks (package-manager)
shopt --set parse_proc

const path = "$REPO_ROOT/spec/testdata/config/package-manager.oil"

const block = parse_hay(path)

hay define Package
const d = eval_hay(block)
write 'level 0 children' $[len(d['children'])]
write 'level 1 children' $[len(d['children'][1]['children'])]

## STDOUT:
level 0 children
3
level 1 children
0
## END


#### Typed Args to Hay Node

shopt --set oil:all

hay define when

# Hm I get 'too many typed args'
# Ah this is because of 'haynode'
# 'haynode' could silently pass through blocks and typed args?

when NAME (x > 0) { 
  const version = '1.0'
  const other = 'str'
}

= _hay()

## STDOUT:
## END


#### OSH and hay (dynamic parsing)

source $REPO_ROOT/spec/testdata/config/osh-hay.osh


## STDOUT:
backticks
eval
TYPE TASK
CODE         
    echo `echo task backticks`
    eval 'echo task eval'
  ___
## END

