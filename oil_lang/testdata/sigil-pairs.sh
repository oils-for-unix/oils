# Demonstrate Oil sigil pairs.
#
# Usage:
#   bin/oil oil_lang/testdata/sigil-pairs.sh
#
# Summary:
#   $() command sub
#   @() string array
#   $[] expr sub
#   @[] primitive typed array
#
# Also used:
#   ${} for ${x %.3f} and ${x|html}
#
# Later:
#   @{} table literals

# Helpers

proc argv {
  python -c 'import sys;print(sys.argv[1:])' @ARGV
}

proc show {
  echo '====='
  argv @ARGV
  echo
}


var strarray = @(
    bare words *.sh {a,b}@example.com 'sq' "dq ${x:-default}"
)

show @strarray

var typedarray = @[
   'quoted' 'words' '*.sh' '{a,b}@example.com' 'sq' "dq ${x:-default}" 
]

show @typedarray

var typedarray2 = @[1.0 2.3 3.4]

show @typedarray2

var cmd_sub = $(
    echo bare words *.sh {a,b}@example.com 'sq' "dq ${x:-default}"
)

show $cmd_sub

# Do we want + as concatenation?  Or use ++ ?
show $['quoted ' + 'words ' + "dq ${x:-default}"]

