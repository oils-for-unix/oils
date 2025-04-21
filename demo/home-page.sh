#!bin/osh

shell-func() {
  echo hi
}

strict-mode() {
  shopt --set strict:all
  if shell-func; then
    echo bad
  fi
}

"$@"
