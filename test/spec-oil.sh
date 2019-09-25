#
# Sourced by test/spec.sh
#

oil-blocks() {
  sh-spec spec/oil-blocks.test.sh --cd-tmp \
    $OSH_LIST "$@"
}

oil-builtins() {
  sh-spec spec/oil-builtins.test.sh --cd-tmp \
    $OSH_LIST "$@"
}

oil-options() {
  sh-spec spec/oil-options.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-expr() {
  sh-spec spec/oil-expr.test.sh --cd-tmp --osh-failures-allowed 7 \
    $OSH_LIST "$@"
}

oil-regex() {
  sh-spec spec/oil-regex.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-func-proc() {
  sh-spec spec/oil-func-proc.test.sh --cd-tmp --osh-failures-allowed 2 \
    $OSH_LIST "$@"
}

oil-builtin-funcs() {
  sh-spec spec/oil-builtin-funcs.test.sh --cd-tmp --osh-failures-allowed 3 \
    $OSH_LIST "$@"
}

# Use bin/oil

oil-keywords() {
  sh-spec spec/oil-keywords.test.sh --cd-tmp --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}


oil-tuple() {
  sh-spec spec/oil-tuple.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OIL_LIST "$@"
}

