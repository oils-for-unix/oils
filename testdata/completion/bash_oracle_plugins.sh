# Common functions fed to 'sh -i' by init_completion.sh.

# OSH should have this built in
if ! type -t _init_completion; then
  source testdata/completion/bash_completion
fi

argv() {
  python -c 'import sys; print(sys.argv[1:])' "$@"
}

argv1() {
  python -c 'import sys; print(repr(sys.argv[1]))' "$@"
}

comp_echo() {
  echo
  echo -n 'case["COMP_WORDS"] = '; argv "${COMP_WORDS[@]}"
}
complete -F comp_echo echo

show_bash_api_vars() {
  echo -n 'case["func_argv"] = '; argv "$@"
  echo -n 'case["COMP_LINE"] = '; argv1 "${COMP_LINE}"
  echo -n 'case["COMP_POINT"] = '; argv1 "${COMP_POINT}"
  echo -n 'case["COMP_WORDS"] = '; argv "${COMP_WORDS[@]}"
  echo -n 'case["COMP_CWORD"] = '; argv1 "${COMP_CWORD}"
}

show_init_completion_vars() {
  echo -n 'case["words"] = '; argv "${words[@]}"
  echo -n 'case["cur"] = '; argv1 "$cur"
  echo -n 'case["prev"] = '; argv1 "$prev"
  echo -n 'case["cword"] = '; argv1 "$cword"
  echo -n 'case["split"] = '; argv1 "$split"
}

_comp_init_completion() {
  show_bash_api_vars "$@"
  local cur prev words cword split

  echo
  echo -n 'case["_init_completion_flags"] = '; argv "$@"
  _init_completion "$@"

  echo
  show_init_completion_vars
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
