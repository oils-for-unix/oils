#!/usr/bin/env bash

echo '--- readlink-demo-data.sh ---'

echo '$0 =' $0
#cat $(dirname $0)/readlink-demo-data.txt

script=$(readlink -f $0)
#script=$(readlink $0)
#script=$(bin/readlink -f $0)

echo "script = $script"

cat $(dirname $script)/readlink-demo-data.txt
