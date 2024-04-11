#!/usr/bin/env sh

mkdir -p _gen/test/utf8
python3 data_lang/utf8_decoder_tests_gen.py >_gen/test/utf8/decoder-exhaustive.inc

# Try to format, but clang-format isn't always available (eg. CI)
if ! clang-format -i _gen/test/utf8/decoder-exhaustive.inc; then
  echo 'Failed to run clang-format on generated decoder tests.'
  echo 'Make sure it is installed if you want _gen/test/utf8/decoder-exhaustive.inc to be human readable.'
fi
