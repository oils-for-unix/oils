# Oil Configuration
#
# The "COWS" pattern


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


#### CI config example
shopt --set oil:basic

# this could be ci.coil too
var config_path = "$REPO_ROOT/spec/testdata/config/ci.oil"

proc task(name, &block) {
  echo "task name=$name"

  # Note: we DON'T use evalblock here!
  #
  # Instead we really want blockstring? or blockstr() ?
  # blockcodestr() ?  We validate the literal code and put it in JSON

  # Note that we accept Oil in addition to shell, but we should probably
  # accept shell.
  #
  # You could have 'sh-task' and 'oil-task' ?
}

task foo {
  echo 'running task foo'
}

shopt --set parse_equals { 
  shvar _DIALECT=sourcehut { # use dialect should FAIL if this isn't set
    # TODO:
    # - need a way to define 'task' only?
    # - don't use 'source'?
    #   - evalpure?

    source $config_path
  }
}

const config = {key: 'val'}
json write :config

## STDOUT:
{"image": "debian/buster"}
## END

