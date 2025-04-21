#!/bin/sh

n=$1
sum=0
i=0
while test $i -lt $n; do
  sum=$(( sum + i ))
  i=$(( i + 1 ))
done
echo "n = $n"
echo "sum = $sum"
