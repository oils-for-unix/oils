## our_shell: ysh
## oils_failures_allowed: 2

#### Changing $PATH before external command will invalidate PATH cache
mkdir -p _tmp/bin
mkdir -p _tmp/bin2
printf '#!/usr/bin/env sh\necho hi\n' >_tmp/bin/hello
printf '#!/usr/bin/env sh\necho hey\n' >_tmp/bin2/hello
chmod +x _tmp/bin/hello
chmod +x _tmp/bin2/hello

BIN=$(pwd)/_tmp/bin
BIN2=$(pwd)/_tmp/bin2

# Will find _tmp/bin/hello
setglobal ENV.PATH="$BIN:$[ENV.PATH]"
hello
echo status=$?

# Should invalidate cache and then find _tmp/bin2/hello
setglobal ENV.PATH="$BIN2:$[ENV.PATH]"
hello
echo status=$?

## STDOUT:
hi
status=0
hey
status=0
## END

#### Changing $PATH before exec will invalidate path cache

mkdir -p _tmp/bin
mkdir -p _tmp/bin2
printf '#!/usr/bin/env sh\necho hi\n' >_tmp/bin/hello
printf '#!/usr/bin/env sh\necho hey\n' >_tmp/bin2/hello
chmod +x _tmp/bin/hello
chmod +x _tmp/bin2/hello

BIN=$(pwd)/_tmp/bin
BIN2=$(pwd)/_tmp/bin2

# Will find _tmp/bin/hello
setglobal ENV.PATH="$BIN:$[ENV.PATH]"
hello
echo status=$?

setglobal ENV.PATH="$BIN2:$[ENV.PATH]"
exec hello
echo status=$?

## STDOUT:
hi
status=0
hey
## END

