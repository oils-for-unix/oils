## our_shell: ysh

#### !== operator
var a = 'bar'

if (a !== 'foo') {
  echo 'not equal'
}

if (a !== 'bar') {
  echo 'should not get here'
}

# NOTE: a !== foo is idiomatic)
if ("$a" !== 'bar') {
  echo 'should not get here'
}

## STDOUT:
not equal
## END


#### elif bug
if (true) {
  echo A
} elif (true) {
  echo B
} elif (true) {
  echo C
} else {
  echo else
}
## STDOUT:
A
## END

#### global vars
builtin set -u

main() {
  source $REPO_ROOT/spec/testdata/global-lib.sh
}

main
test_func

## status: 1
## STDOUT:
## END

#### Julia port

# https://lobste.rs/s/ritbgc/what_glue_languages_do_you_use_like#c_nhikri
#
# See bash counterpart in spec/blog1.test.sh

git-branch-merged() {
  cat <<EOF
  foo
* bar
  baz
  master
EOF
}

# With bash-style readarray.  The -t is annoying.
git-branch-merged | while read --line {
  # Note: this can't be 'const' because const is dynamic like 'readonly'.  And
  # we don't have block scope.
  var line = _reply->strip()  # removing leading space

  # with glob: line ~~ '\**'           (awkward)
  # with regex: line ~ / %start '*' /  (not terrible, but somewhat complex)

  # Other ideas:
  # line `startswith` 'a'
  # line `endswith` 'b'

  # line %startswith 'a'
  # line %endswith 'b'

  if (line !== 'master' and not line->startswith('*')) {
    echo $line
  }
} | readarray -t :branches

# TODO: I think we want read --lines :branches ?  Then we don't need this
# conversion.
var branchList = :| "${branches[@]}" |

if (len(branchList) === 0) {
  echo "No merged branches"
} else {
  write git branch -D @branchList
}

# With "append".  Hm read --lines isn't bad.
var branches2 = :| |
git-branch-merged | while read --line {
  var line2 = _reply->strip()  # removing leading space
  if (line2 !== 'master' and not line2->startswith('*')) {
    append $line2 (branches2)
  }
}

write -- ___  @branches2

## STDOUT:
git
branch
-D
foo
baz
___
foo
baz
## END

#### readonly in loop: explains why const doesn't work

# TODO: Might want to change const in Oil...
# bash actually prevents assignment and prints a warning, DOH.

seq 3 | while read -r line; do
  readonly stripped=${line//1/x}
  #declare stripped=${line//1/x}
  echo $stripped
done
## status: 1
## STDOUT:
x
## END


#### Eggex bug in a loop

# https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/A.20list.20of.20feedback
for i in @(seq 2) {
  # BUG: This crashes here, but NOT when extracted!  Bad.
  var pat = / 'test' word+ /
  if ("test$i" ~ pat) {
    echo yes
  }
}
## STDOUT:
yes
yes
## END


#### Append object onto Array
var e = []

# %() is also acceptable, but we prefer Python-like [] for objects.
# %() is more for an array of strings
# var e = %()

for i in @(seq 2) {
  var o = {}
  setvar o[i] = "Test $i"

  # push builtin is only for strings

  call e->append(o)
}

json write (e)

## STDOUT:
[
  {
    "1": "Test 1"
  },
  {
    "2": "Test 2"
  }
]
## END

#### Invalid op on string
shopt -s oil:all

var clients = {'email': 'foo', 'e2': 'bar'}
for c in (clients) {
  echo $c
  # A user tickled this.  I think this should make the whole 'const' line fail
  # with code 1 or 2?
  const e = c.email
}
## status: 3
## STDOUT:
email
## END
