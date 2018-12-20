# Common functions fed to 'sh -i' by init_completion.sh.

# OSH should have this built in
if ! type -t _init_completion; then
  source testdata/completion/bash_completion
fi

argv() {
  python -c 'import sys; print(sys.argv[1:])' "$@"
}
comp_echo() {
  echo
  echo -n 'COMP_WORDS '; argv "${COMP_WORDS[@]}"
}
complete -F comp_echo echo

showvars() {
  echo -n 'WORDS '; argv "${words[@]}"
  echo -n 'VAR '; argv cur "$cur"
  echo -n 'VAR '; argv prev "$prev"
  echo -n 'VAR '; argv cword "$cword"
  echo -n 'VAR '; argv split "$split"
}

_comp_init_completion() {
  local cur prev words cword split

  echo
  echo FLAGS "$@"
  _init_completion "$@"

  echo
  showvars
}

noflags() { echo; }
comp_noflags() { _comp_init_completion; }
complete -F comp_noflags noflags

s() { echo; }
comp_s() { _comp_init_completion -s ; }
complete -F comp_s s

n() { echo; }
comp_n() { _comp_init_completion -n = ; }
complete -F comp_n n

n2() { echo; }
comp_n2() { _comp_init_completion -n := ; }
complete -F comp_n2 n2
