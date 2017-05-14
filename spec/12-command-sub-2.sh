#!/bin/bash

echo $(echo foo)

echo $(echo foo
echo bar
)

echo $(cat <<EOF
hi
EOF
)
