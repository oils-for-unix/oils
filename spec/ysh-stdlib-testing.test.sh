## our_shell: ysh
## oils_failures_allowed: 1

# Hm can we do this entirely in user code, not as a builtin?

#### Describe Prototype

source --builtin testing.ysh

proc p {
  echo STDOUT
  echo STDERR >& 2
  return 42
}

describe p {
  # each case changes to a clean directory?
  #
  # and each one is numbered?

  it 'prints to stdout and stderr' {
    try {
      p > out 2>& err
    }
    assert (_status === 42)

    cat out
    cat err

    # Oh man the here docs are still useful here because of 'diff' interface
    # Multiline strings don't quite do it

    diff out - <<< '''
    STDOUT
    '''

    diff err - <<< '''
    STDERR
    '''
  }
}

## STDOUT:
TODO
## END
