# Test out Oil's JSON support.

#### json echo STRING
s='foo'
json echo s
## STDOUT:
"foo"
## END

#### json echo ARRAY
a=(foo.cc foo.h)
json echo a
json echo -indent 0 a
## STDOUT:
[
  "foo.cc",
  "foo.h"
]
[
"foo.cc",
"foo.h"
]
## END
