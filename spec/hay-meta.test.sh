# Hay Metaprogramming

#### Conditional Inside Blocks
shopt --set oil:all

hay define Rule

const DEBUG = true

Rule one {
  if (DEBUG) {
    deps = 'foo'
  } else {
    deps = 'bar'
  }
}

json write (_hay()) | jq '.children[0]' > actual.txt

diff -u - actual.txt <<EOF
{
  "type": "Rule",
  "args": [
    "one"
  ],
  "children": [],
  "attrs": {
    "deps": "foo"
  }
}
EOF

## STDOUT:
## END


#### Conditional Outside Block
shopt --set oil:all

hay define Rule

const DEBUG = true

if (DEBUG) {
  Rule two {
    deps = 'spam'
  } 
} else {
  Rule two {
    deps = 'bar'
  } 
}

json write (_hay()) | jq '.children[0].attrs' > actual.txt

diff -u - actual.txt <<EOF
{
  "deps": "spam"
}
EOF

## STDOUT:
## END


#### Iteration Inside Block
shopt --set oil:all

hay define Rule

Rule foo {
  var d = {}
  # private var with _
  for name_ in spam eggs ham {
    setvar d[name_] = true
  }
}

json write (_hay()) | jq '.children[0].attrs' > actual.txt

# For loop name leaks!  Might want to make it "name_" instead!

#cat actual.txt

diff -u - actual.txt <<EOF
{
  "d": {
    "spam": true,
    "eggs": true,
    "ham": true
  }
}
EOF


## STDOUT:
## END


#### Iteration Outside Block
shopt --set oil:all

hay define Rule

for name in spam eggs ham {
  Rule $name {
    path = "/usr/bin/$name"
  }
}

json write (_hay()) | jq '.children[].attrs' > actual.txt

diff -u - actual.txt <<EOF
{
  "path": "/usr/bin/spam"
}
{
  "path": "/usr/bin/eggs"
}
{
  "path": "/usr/bin/ham"
}
EOF

## STDOUT:
## END


#### Proc Inside Block
shopt --set oil:all

hay define rule  # lower case allowed

proc p(name; out) {
  echo 'p'
  call out->setValue(name)
}

rule hello {
  var eggs = ''
  var bar = ''

  p spam (&eggs)
  p foo (&bar)
}

json write (_hay()) | jq '.children[0].attrs' > actual.txt

diff -u - actual.txt <<EOF
{
  "eggs": "spam",
  "bar": "foo"
}
EOF

## STDOUT:
p
p
## END



#### Proc That Defines Block
shopt --set oil:all

hay define Rule

proc myrule(name) {

  # Each haynode has its own scope.  But then it can't see the args!  Oops.
  # Is there a better way to do this?

  shopt --set dynamic_scope {
    Rule $name {
      path = "/usr/bin/$name"
    }
  }
}

myrule spam
myrule eggs
myrule ham

json write (_hay()) | jq '.children[].attrs' > actual.txt

diff -u - actual.txt <<EOF
{
  "path": "/usr/bin/spam"
}
{
  "path": "/usr/bin/eggs"
}
{
  "path": "/usr/bin/ham"
}
EOF

## STDOUT:
## END

