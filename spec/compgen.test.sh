#!/usr/bin/env bash

#### Print function list
env -i /bin/bash --norc --noprofile -c 'add () { expr 4 + 4; }; \
                                        div () { expr 6 / 2; }; \
                                        ek () { echo hello;} \
                                        && compgen -A function'
## status: 0
## STDOUT:
add
div
ek
## END
