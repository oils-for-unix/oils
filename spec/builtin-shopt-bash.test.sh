## compare_shells: bash
## oils_failures_allowed: 0

# builtin-shopt-bash.test.sh

#### shopt
shopt | grep inherit_errexit | tr -d ' '
## stdout-json: "inherit_errexit\toff\n"

#### shopt -p
shopt -p | grep inherit_errexit
## STDOUT:
shopt -u inherit_errexit
## END

#### shopt -o
shopt -o | grep errexit | tr -d ' '
## stdout-json: "errexit\toff\n"

#### shopt -p -o
shopt -p -o | grep errexit
## STDOUT:
set +o errexit
## END
