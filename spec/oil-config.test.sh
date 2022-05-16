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


#### CI config with task blocks
shopt --set oil:basic

# this could be ci.coil too
var config_path = "$REPO_ROOT/spec/testdata/config/ci.oil"

proc task(name, block Block) {
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

    # maybe '-external' for external commands?
    # +external/echo to allow just one?
    # That is similar to 'use bin'

    const first_words = %( +proc/task +builtin/{echo,write,printf} )

    # Possible syntaxes:
    # - no sigil: proc/task
    # - % which are like symbols, would be confusing
    # - other namespaces:
    #   - +alias/myalias
    #   - +option/errexit
    #   - coprocess, container?
    # - shopt_get('+option/errexit') ?  Make it first class?

    # TODO: This should be bin/oven --source ci_dialect.oil -- myconfig.oil
    # Do we also need --source-after?  or -c after?

    # Or we can do bin/oil --source ci_dialect.oil -- myconfig.oil

    const config = _vm_eval(config_path, first_words)
  }
}

json write (config)

## STDOUT:
{"image": "debian/buster"}
## END

#### Dict Blocks

# first words has to be dynamic I think?
#
# push-proc package user {
#   const config = _vm_eval('spec/testdata/config/package-manger.oil')
# }
#
# Implement with ctx_Proc().  Yeah that needs to be a stack just ilke the
# option stack!
#
# Or
#
# push --proc package --proc user --no-external {
#
# }

const config = _vm_eval('spec/testdata/config/package-manager.oil', %(package user))

## STDOUT:
TODO
## END

