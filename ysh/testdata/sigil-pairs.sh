# Demonstrate Oil sigil pairs.
#
# Usage:
#   bin/oil oil_lang/testdata/sigil-pairs.sh
#
# Summary:
#   $() command sub
#   %() string array
#   $[] expr sub
#
# Also used:
#   ${} for ${x %.3f} and ${x|html}
#
# Later:
#   @{} table literals

# Helpers

argv() {
  python -c 'import sys;print(sys.argv[1:])' @ARGV
}

show() {
  echo '====='
  argv @ARGV
  echo
}


var strarray = %(
    bare words *.sh {a,b}@example.com 'sq' "dq ${x:-default}"
)

show @strarray

var cmd_sub = $(
    echo bare words *.sh {a,b}@example.com 'sq' "dq ${x:-default}"
)

show $cmd_sub

show $['quoted ' ++ 'words ' ++ "dq ${x:-default}"]

