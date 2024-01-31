# for spec/oil-builtin-pp.test.sh

f() {
  ### doc ' comment with " quotes
  echo
}

g() {
  echo hi
  ### not a doc comment
}

proc myproc {
  ### YSH-style proc
  echo myproc
}

