#!/usr/bin/env python2
"""
spelling.py

Filter the output of 'lynx -dump' into a list of words to spell check.
"""
from __future__ import print_function

from collections import Counter
import optparse
import re
import sys

from doctools.util import log


def SplitWords(contents):
  # Remove URLs so path components don't show up as words
  contents = re.sub(r'(http|https|file)://\S+', '', contents)

  # Take into account contractions with apostrophes
  #
  # - doesn't
  # - can't

  WORD_RE = re.compile(r'''
  [a-zA-Z]+
  (?:\'t\b)?  # optional contraction
  ''', re.VERBOSE)

  words = WORD_RE.findall(contents)

  for w in words:
    yield w


def WordList(f):
  for line in f:
    # no special characters allowed
    yield line.strip()


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser()
  p.add_option(
      '--known-words', dest='known_words',
      help='List of words like /usr/share/dict/words')
  p.add_option(
      '--more-than-bash', dest='more_than_bash', type=int, default=0,
      help='Expected number of cases where OSH starts more processes than bash')
  return p


def main(argv):
  o = Options()
  opts, argv = o.parse_args(argv[1:])

  action = argv[0]

  if action == 'word-split':
    contents = sys.stdin.read()
    for w in SplitWords(contents):
      print(w)

  elif action == 'check':
    word_files = argv[1:]

    d = Counter()

    for path in word_files:
      with open(path) as f:
        for word in WordList(f):
          d[word] += 1

    print('')
    print('Most common words')
    print('')
    for word, count in d.most_common()[:20]:
      print('%10d %s' % (count, word))

    print('')
    print('Least common words')
    print('')
    for word, count in d.most_common()[-20:]:
      print('%10d %s' % (count, word))

    log('%d word files', len(word_files))
    log('%d unique words', len(d))

    known_words = {}
    with open(opts.known_words) as f:
      for w in WordList(f):
        known_words[w] = True

    print('')
    print('Potential Misspellings')
    print('')

    for path in word_files:

      print()
      print('\t%s' % path)
      print()

      with open(path) as f:
        unknown = {}
        for w in WordList(f):
          #if d.get(word) == 1:
          #  print(word)
          if w.lower() not in known_words:
            unknown[w] = True

        if unknown:
          for u in sorted(unknown):
            # only occurs once
            if d.get(u) == 1:
              print(u)
          log('\t%d unknown words in %s', len(unknown), path)


    # Checking algorithms:
    #
    # - Does it appear in the dictionary?  Problem: most computer terms
    # - Does it appear only once or twice in the whole corpus?
    # - Is the edit distance very close to a dictinoary word?
    #   - e.g. subsitutions is a typo

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
