# For spec/introspect.test.sh
argv.py '  @' "${FUNCNAME[@]}"
argv.py '  0' "${FUNCNAME[0]}"
argv.py '${}' "${FUNCNAME}"
argv.py '  $' "$FUNCNAME"
