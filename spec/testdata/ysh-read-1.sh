# Called from spec/ysh-builtins.test.sh

shopt -s ysh:upgrade

# Hm this preserves the newline?
seq 3 | while read --raw-line {
  write reply=$_reply # implicit
}
write a b | while read --raw-line --with-eol (&myline) {
  write --end '' myline=$myline
}
