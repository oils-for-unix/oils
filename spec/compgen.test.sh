#!/usr/bin/env bash

#### Print function list
env -i /bin/bash --norc --noprofile -c 'add () { expr 4 + 4; }; \
                                        div () { expr 6 / 2; }; \
                                        ek () { echo hello; }; \
                                        __ec () { echo hi; }; \
                                        _ab () { expr 10 % 3; }; \
                                        compgen -A function'
## status: 0
## STDOUT:
__ec
_ab
add
div
ek
## END
