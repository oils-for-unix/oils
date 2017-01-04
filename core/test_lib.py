#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
test_lib.py - Functions for testing.
"""

def TokensEqual(left, right):
  # Ignoring location in CompoundObj.__eq__ now, but we might want this later.
  #return left.id == right.id and left.val == right.val
  return left == right


def TokenWordsEqual(left, right):
  # Ignoring location in CompoundObj.__eq__ now, but we might want this later.
  #return TokensEqual(left.token, right.token)
  return left == right
