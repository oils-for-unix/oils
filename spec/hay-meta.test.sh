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

= _hay()

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

= _hay()

## STDOUT:
## END


#### Iteration Inside Block
shopt --set oil:all

hay define Rule

Rule foo {
  var d = {}
  for name in spam eggs ham {
    setvar d->name = true
  }
}

= _hay()

## STDOUT:
TODO
## END


#### Iteration Outside Block
shopt --set oil:all

hay define Rule

for name in spam eggs ham {
  Rule $name {
    path = "/usr/bin/$name"
  }
}

json write (_hay())

## STDOUT:
TODO
## END


#### Proc Inside Block
shopt --set oil:all

hay define rule

# Does this do anything?
# Maybe setref?
proc p(name, :out) {
  echo 'p'
  setref out = name
}

rule hello {
  var eggs = ''
  var bar = ''

  p spam :eggs
  p foo :bar
}

= _hay()

## STDOUT:
TODO
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

= _hay()


## STDOUT:
TODO
## END

