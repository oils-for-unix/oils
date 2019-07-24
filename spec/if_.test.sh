#!/usr/bin/env bash
#
# Test the if statement

#### If
if true; then
  echo if
fi
## stdout: if

#### else
if false; then
  echo if
else
  echo else
fi
## stdout: else

#### elif
if (( 0 )); then
  echo if
elif true; then
  echo elif
else
  echo else
fi
## stdout: elif

#### Long style
if [[ 0 -eq 1 ]]
then
  echo if
  echo if
elif true
then
  echo elif
else
  echo else
  echo else
fi
## stdout: elif

