## compare_shells: bash dash mksh zsh ash
## oils_failures_allowed: 0

# bugs we ran into in ./configure
#
# - old version of dash: doesn't unset _do_fork=0
# - old version of bash on OS X: background job and if command time -f

#### ./configure idiom
set -o errexit
if command time -f '%e %M' true; then
  echo 'supports -f'
  command time -f '%e %M' true
fi
## STDOUT:
supports -f
## END
