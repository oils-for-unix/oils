#!/usr/bin/env bash
#
# Usage:
#   data_lang/json-survey.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH

decode-int-float() {
  # This is a float
  python2 -c 'import json; val = json.loads("1e6"); print(type(val)); print(val)'
  python2 -c 'import json; val = json.loads("1e-6"); print(type(val)); print(val)'
  python2 -c 'import json; val = json.loads("0.5"); print(type(val)); print(val)'

  # Int
  python2 -c 'import json; val = json.loads("42"); print(type(val)); print(val)'

  python3 -c 'import json; val = json.loads("1e6"); print(type(val)); print(val)'

  echo
  echo

  # JavaScript only has 'number', no Int and Float
  nodejs -e 'var val = JSON.parse("1e6"); console.log(typeof(val)); console.log(val)'
}

decode-syntax-errors() {

  python2 -c 'import json; val = json.loads("{3:4}"); print(type(val)); print(val)' || true
  echo
  python2 -c 'import json; val = json.loads("[3:4]"); print(type(val)); print(val)' || true

  echo
  echo

  # This has good position information
  # It prints the line number, the line, and points to the token in the line
  # where the problem happened

  nodejs -e 'var val = JSON.parse("{3: 4}"); console.log(typeof(val)); console.log(val)' || true

  nodejs -e 'var val = JSON.parse("[\n  3: 4\n]"); console.log(typeof(val)); console.log(val)' || true

  nodejs -e 'var val = JSON.parse("[\n\n \"hello "); console.log(typeof(val)); console.log(val)' || true
}

decode-empty-input() {
  python3 -c 'import json; val = json.loads(""); print(type(val)); print(val)' || true

  echo
  echo

  nodejs -e 'var val = JSON.parse(""); console.log(typeof(val)); console.log(val)' || true
}

decode-invalid-escape() {
  # single quoted escape not valid
  cat >_tmp/json.txt <<'EOF'
"\'"
EOF
  local json
  json=$(cat _tmp/json.txt)

  python3 -c 'import json, sys; val = json.loads(sys.argv[1]); print(type(val)); print(val)' \
    "$json" || true

  echo
  echo

  nodejs -e 'var val = JSON.parse(process.argv[1]); console.log(typeof(val)); console.log(val)' \
    "$json" || true
}

encode-list-dict-indent() {
  echo 'PYTHON'
  python3 -c 'import json; val = {}; print(json.dumps(val, indent=4))'
  python3 -c 'import json; val = {"a": 42}; print(json.dumps(val, indent=4))'
  python3 -c 'import json; val = {"a": 42, "b": 43}; print(json.dumps(val, indent=4))'
  python3 -c 'import json; val = []; print(json.dumps(val, indent=4))'
  python3 -c 'import json; val = [42]; print(json.dumps(val, indent=4))'
  echo

  echo 'JS'
  nodejs -e 'var val = {}; console.log(JSON.stringify(val, null, 4))'
  nodejs -e 'var val = {"a": 42}; console.log(JSON.stringify(val, null, 4))'
  nodejs -e 'var val = {"a": 42, "b": 43}; console.log(JSON.stringify(val, null, 4))'
  nodejs -e 'var val = []; console.log(JSON.stringify(val, null, 4))'
  nodejs -e 'var val = [42]; console.log(JSON.stringify(val, null, 4))'
  echo
}

encode-obj-cycles() {
  python3 -c 'import json; val = {}; val["k"] = val; print(json.dumps(val))' || true
  echo

  python3 -c 'import json; val = []; val.append(val); print(json.dumps(val))' || true
  echo

  # Better error message than Python!
  # TypeError: Converting circular structure to JSON
  #  --> starting at object with constructor 'Object'
  #  --- property 'k' closes the circle
  nodejs -e 'var val = {}; val["k"] = val; console.log(JSON.stringify(val))' || true
  echo

  nodejs -e 'var val = []; val.push(val); console.log(JSON.stringify(val))' || true
  echo
}

multiple-refs() {
  # Python prints a tree
  python3 -c 'import json; mylist = [1,2,3]; val = [mylist, mylist]; print(repr(val)); print(json.dumps(val))'
  echo

  # Same with node.js
  nodejs -e 'var mylist = [1,2,3]; var val = [mylist, mylist]; console.log(val); console.log(JSON.stringify(val))'
  echo

  # Same with Oils
  bin/osh -c 'var mylist = [1,2,3]; var val = [mylist, mylist]; = val; json write (val); pp asdl (val)'
  echo
}

oils-cycles() {
  bin/ysh -c 'var d = {}; setvar d.key = d; = d; pp line (d); pp asdl (d); json write (d)'
}

surrogate-pair() {
  local json=${1:-'"\ud83e\udd26"'}

  # Hm it actually escapes.  I thought it would use raw UTF-8
  python2 -c 'import json; s = json.loads(r'\'$json\''); print(json.dumps(s))'
  echo

  python3 -c 'import json; s = json.loads(r'\'$json\''); print(json.dumps(s))'
  echo

  # This doesn't escape
  nodejs -e 'var s = JSON.parse('\'$json\''); console.log(JSON.stringify(s))'
  echo
}

surrogate-half() {
  local json='"\ud83e"'

  # Round trips correctly!
  surrogate-pair "$json"
}

encode-nan() {
  # Wow Python doesn't conform to spec!!
  # https://docs.python.org/3.8/library/json.html#infinite-and-nan-number-values

  # allow_nan=False and parse_constant alter the behavior

  python2 -c 'import json; val = float("nan"); s = json.dumps(val); print(s); print(json.loads(s))' || true
  echo

  python3 -c 'import json; val = float("nan"); s = json.dumps(val); print(s); print(json.loads(s))' || true
  echo

  python3 -c 'import json; val = float("nan"); s = json.dumps(val, allow_nan=False); print(s); print(json.loads(s))' || true
  echo

  # nodejs uses null
  nodejs -e 'var val = NaN; var s = JSON.stringify(val); console.log(s); console.log(JSON.parse(s));' || true
  echo
}

encode-inf() {
  # Again, Python doesn't conform to spec

  python2 -c 'import json; val = float("-inf"); print(val); s = json.dumps(val); print(s); print(json.loads(s))' || true
  echo

  python3 -c 'import json; val = float("-inf"); print(val); s = json.dumps(val); print(s); print(json.loads(s))' || true
  echo

  python3 -c 'import json; val = float("-inf"); print(val); s = json.dumps(val, allow_nan=False); print(s); print(json.loads(s))' || true
  echo

  # nodejs uses null again
  nodejs -e 'var val = Number.NEGATIVE_INFINITY; console.log(val); var s = JSON.stringify(val); console.log(s); console.log(JSON.parse(s));' || true
  echo
}

encode-bad-type() {
  python3 -c 'import json; print(json.dumps(json))' || true
  echo

  # {} or undefined - BAD!
  nodejs -e 'console.log(JSON.stringify(JSON));' || true
  nodejs -e 'function f() { return 42; }; console.log(JSON.stringify(f));' || true
  echo
}

encode-binary-data() {
  # utf-8 codec can't decode byte -- so it does UTF-8 decoding during encoding,
  # which makes sense
  python2 -c 'import json; print(json.dumps(b"\xff"))' || true
  echo

  # can't serialize bytes type
  python3 -c 'import json; print(json.dumps(b"\xff"))' || true
  echo

  # there is no bytes type?  \xff is a code point in JS
  nodejs -e 'console.log(JSON.stringify("\xff"));' || true
  nodejs -e 'console.log(JSON.stringify("\u{ff}"));' || true
  echo
}

decode-utf8-in-surrogate-range() {
  python2 -c 'b = "\xed\xa0\xbe"; print(repr(b.decode("utf-8")))'
  echo

  # Hm Python 3 gives an error here!
  python3 -c 'b = b"\xed\xa0\xbe"; print(repr(b.decode("utf-8")))' || true
  echo

  # valid
  nodejs -e 'var u = new Uint8Array([0xce, 0xbc]); var string = new TextDecoder("utf-8").decode(u); console.log(string);'
  echo

  # can't decode!
  nodejs -e 'var u = new Uint8Array([0xed, 0xa0, 0xbe]); var string = new TextDecoder("utf-8").decode(u); console.log(string);'
  echo
}

pairs() {
  local nums
  nums=$(seq $1)

  echo -n '['
  for i in $nums; do
    echo -n '[42,'
  done
  echo -n '43]'
  for i in $nums; do
    echo -n ']'
  done
}

decode-deeply-nested() {
  local msg
  msg=$(pairs 40200)

  # RuntimeError
  echo "$msg" | python2 -c 'import json, sys; print(repr(json.load(sys.stdin)))' || true

  # RecursionError
  echo "$msg" | python3 -c 'import json, sys; print(repr(json.load(sys.stdin)))' || true

  # Hm node.js handles it fine?  Probably doesn't have a stackful parser.
  # [ [ [ [Array] ] ] ]
  echo "$msg" | nodejs -e 'var fs = require("fs"); var stdin = fs.readFileSync(0, "utf-8"); console.log(JSON.parse(stdin));' || true

  echo "$msg" | bin/osh -c 'json read; = _reply' || true

  # Hm this works past 40K in C++!  Then segmentation fault.  We could put an
  # artifical limit on it.
  local osh=_bin/cxx-opt/osh
  ninja $osh
  echo "$msg" | $osh -c 'json read; = _reply; echo $[len(_reply)]' || true
}

"$@"
