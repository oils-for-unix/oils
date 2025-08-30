## oils_failures_allowed: 2

#### Match tab character with [\t]
shopt -s ysh:all

var pat = / ('a' [\t] 'b') /
pp test_ (str(pat))

var lines = :| b'aa\tbb' b'cc\tdd' |
write @lines | egrep $pat | od -A n -t c 

## STDOUT:
(Str)   "(a[\t]b)"
   a   a  \t   b   b  \n
## END

#### Match newline with [\n]
shopt -s ysh:all

var pat = / [\n] /

pp test_ (str(pat))

pp test_ ('z' ~ pat)

# this matches
pp test_ (b'\n' ~ pat)

# but then what happens with grep?
# invalid regular expression

# write 1 2 3 | egrep "$pat"

## STDOUT:
(Str)   "[\n]"
(Bool)   false
(Bool)   true
## END

#### ERE: 'dot' matches newline

= 'z' ~ /dot/
= b'\n' ~ /dot/
= '' ~ /dot/

## STDOUT:
(Bool)  true
(Bool)  true
(Bool)  false
## END

#### ERE: 'dot' matches code point represented with multiple bytes (mu = 0xce 0xbe)

var pat = / 'a' dot 'b' /

pp test_ ('axb' ~ pat )
# mu character
pp test_ (b'a\yce\ybcb' ~ pat )
pp test_ (b'a\u{3bc}b' ~ pat )

pp test_ ('ab' ~ pat )
pp test_ ('aZZb' ~ pat )

## STDOUT:
(Bool)   true
(Bool)   true
(Bool)   true
(Bool)   false
(Bool)   false
## END

#### $'\xff' is disallowed in Eggex, because it's disallowed in YSH

# NOTE: This pattern doesn't work with en_US.UTF-8.  I think the user should
# set LANG=C or shopt --unset libc_utf8.

shopt -s ysh:all
=  /[ $'\xff' ]/;

## status: 1
## STDOUT:
## END

#### Match low ASCII with [\x01]
shopt -s ysh:all

pp test_ ('a' ~ / [a] /)
echo

pp test_ (b'\y01' ~ / [\x01] /)
pp test_ (b'\y02' ~ / [\x01] /)

# \y01 isn't accepted, because we punt \x01 translation to ERE ...
#pp test_ (b'\y02' ~ / [\y01] /)

# we print this as \u{1}
# = str( / [\x01] / )

## STDOUT:
(Bool)   true

(Bool)   true
(Bool)   false
## END

#### Match low ASCII with \u{7f} - translates to valid ERE
shopt -s ysh:all
var pat = /[ \u{7f} ]/;

echo $pat | od -A n -t x1
if (b'\y7f' ~ pat) { echo yes } else { echo no }
if (b'\y7e' ~ pat) { echo yes } else { echo no }

var pat2 = /[ \u{7f} ]/;
var pat3 = /[ \u{0007f} ]/;
test "$pat2" = "$pat3" && echo 'equal'

var range = / [ \u{70} - \u{7f} ] /
if (b'\y70' ~ range) { echo yes } else { echo no }
if (b'\y69' ~ range) { echo yes } else { echo no }

## STDOUT:
 5b 7f 5d 0a
yes
no
equal
yes
no
## END

#### Can't match code points \u{ff} because they don't translate to valid ERE
shopt -s ysh:all
var pat2 = /[ \u{00} - \u{ff} ]/;

# This causes an error
echo $pat2

# This just prints it
= pat2

var pat1 = /[ \u{ff} ]/;

echo $pat1 | od -A n -t x1
if (b'\x7f' ~ pat) { echo yes } else { echo no }
if (b'\x7e' ~ pat) { echo yes } else { echo no }

## status: 1
## stdout-json: ""

#### non-ASCII bytes must be singleton terms, e.g. b'\y7f\yff' is disallowed
var bytes = b'\y7f\yff'
var pat = / [ @bytes ] /
echo $pat
## status: 1
## stdout-json: ""

#### Bytes are denoted \y01 in Eggex char classes (not \x01)

# That is, eggex does have MODES like re.UNICODE
#
# We UNAMBIGUOUSLY accept
# - \y01 or \u{1} - these are the same
# - \yff or \u{ff} - these are DIFFERENT

var pat = / [\y01] /
pp test_ (b'\y01' ~ pat)
pp test_ ('a' ~ pat)

## STDOUT:
(Bool)   true
(Bool)   false
## END

#### NUL byte can be expressed in Eggex, but not in ERE

$SH <<'EOF'
pp test_ (b'\y01' ~ / [\y01] /)
pp test_ (b'\y00' ~ / [\y00] /)
EOF
echo status=$?

$SH <<'EOF'
pp test_ (b'\y01' ~ / [\u{1}] /)
pp test_ (b'\y00' ~ / [\u{0}] /)
EOF
echo status=$?


# legacy synonym

$SH <<'EOF'
pp test_ (b'\y01' ~ / [\x01] /)
pp test_ (b'\y00' ~ / [\x00] /)
EOF
echo status=$?

## STDOUT:
(Bool)   true
status=1
(Bool)   true
status=1
(Bool)   true
status=1
## END

#### High bytes 0x80 0xff usually can't be matched - Eggex is UTF-8
shopt -s ysh:all

# ascii works
pp test_ (b'\y7f' ~ / [\x7f] /)
pp test_ (b'\y7e' ~ / [\x7f] /)
echo

# BUG before disabling: high byte doesn't work?    Because of utf-8 locale
#
# We translate \x80 to a the byte b'\y80', but it still doesn't work
#
# We COULD allow this with LANG=C, but for now don't bother.  I think using an
# ERE string is probably better.

pp test_ (b'\y80' ~ / [\x80] /)
pp test_ (b'\yff' ~ / [\xff] /)

= str( / [\x80]/ )

## STDOUT:
## END

#### High bytes 0x80 0xff can be matched with plain ERE and LC_ALL=C

export LC_ALL=C

$SH <<'EOF'
var yes = b'foo \yff'
var no = b'foo'

# POSIX ERE string
var ere = b'[\yff]'

pp test_ (yes ~ ere)
pp test_ (no ~ ere)
EOF

## STDOUT:
(Bool)   true
(Bool)   false
## END
