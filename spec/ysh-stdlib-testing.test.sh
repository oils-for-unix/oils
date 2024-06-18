## our_shell: ysh

#### Test framework

source --builtin testing.ysh
setglobal _test_use_color = false

test_suite "three bad tests" {
    test_case "the assertion is false" {
        assert [1 > 0]
        assert [1 > 1]
        assert [1 > 2]
    }

    test_case "there is an exception while evaluating the assertion" {
        assert ["Superman" > "Batman"]
    }

    test_case "there is an exception outside of any assertion" {
        error "oops!"
    }
}

test_case "one good test case" {
    assert [1 === 1]
    assert [2 === 2]
}

run_tests

## STDOUT:
begin three bad tests
    test the assertion is false ...
        assertion FAILED
    test there is an exception while evaluating the assertion ...
        assertion ERRORED: 10
    test there is an exception outside of any assertion ...
        ERROR: 10
end
test one good test case ... ok
3 / 4 tests failed
## END

#### Stdout and stderr

source --builtin testing.ysh
setglobal _test_use_color = false

proc p {
  echo STDOUT
  echo STDERR >& 2
  return 42
}

test_case "that it prints to stdout and stderr" {
  # each case changes to a clean directory?
  #
  # and each one is numbered?

  try {
    p > out 2> err
  }

  assert [_status === 42]
  assert [$(<out) === "STDOUT"]
  assert [$(<err) === "STDERR"]
}

run_tests

## STDOUT:
test that it prints to stdout and stderr ... ok
1 tests succeeded
## END

# #### ysh --tool test file
# 
# cat >mytest.ysh <<EOF
# echo hi
# EOF
# 
# # which ysh
# 
# # the test framework sets $SH to bin/ysh
# # but ysh is already installed on this machine
# 
# $SH --tool test mytest.ysh
# 
# ## STDOUT:
# ## END
# 
# # Hm can we do this entirely in user code, not as a builtin?
