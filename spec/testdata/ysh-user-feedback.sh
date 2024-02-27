# Called from spec/ysh-user-feedback
#
# Spec test framework reads code from stdin, which conflicts with read --line

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
git-branch-merged | while read -r line {
  # Note: this can't be 'const' because const is dynamic like 'readonly'.  And
  # we don't have block scope.
  var line = line => trim()  # removing leading space

  # with glob: line ~~ '\**'           (awkward)
  # with regex: line ~ / %start '*' /  (not terrible, but somewhat complex)

  if (line !== 'master' and not line => startsWith('*')) {
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
git-branch-merged | while read -r line {
  var line2 = line => trim()  # removing leading space
  if (line2 !== 'master' and not line2->startsWith('*')) {
    append $line2 (branches2)
  }
}

write -- ___  @branches2

