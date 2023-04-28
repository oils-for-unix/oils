#!/usr/bin/env python2
"""
spec_osh.py
"""
from __future__ import print_function

def Define(sp):
  # Isolate it in its own test suite because of job control issue
  sp.File('interactive', suite='interactive')

  # Also uses $SH -i quite a bit
  sp.File('sh-options', suite='interactive')
  sp.File('sh-usage', suite='interactive')

  # one cases uses -i
  sp.File('var-num', suite='interactive')


  #
  # suite osh
  #

  sp.File('alias')

  sp.File('append')

  sp.File('arith')

  sp.File('arith-context')

  sp.File('array')

  sp.File('array-compat')

  sp.File('assign')

  sp.File('assign-deferred')

  sp.File('assign-dialects')

  sp.File('assign-extended')

  sp.File('assoc')

  sp.File('assoc-zsh')

  sp.File('background')

  sp.File('ble-features')

  sp.File('ble-idioms')

  sp.File('blog1')

  sp.File('blog2')

  sp.File('brace-expansion')

  sp.File('bugs')

  sp.File('builtin-bash')

  sp.File('builtin-bracket')

  sp.File('builtin-completion')

  sp.File('builtin-dirs')

  sp.File('builtin-eval-source')

  sp.File('builtin-getopts')

  sp.File('builtin-io')

  sp.File('builtin-printf')

  sp.File('builtins')

  sp.File('builtins2')

  sp.File('builtin-special')

  sp.File('builtin-times')

  sp.File('builtin-trap')

  sp.File('builtin-trap-bash')

  sp.File('builtin-vars')

  sp.File('case_')

  sp.File('command_')

  sp.File('command-parsing')

  sp.File('command-sub')

  sp.File('comments')

  sp.File('dbracket')

  sp.File('dparen')

  sp.File('empty-bodies')

  sp.File('errexit')

  sp.File('errexit-oil')

  sp.File('exit-status')

  sp.File('explore-parsing')

  sp.File('extglob-files')

  sp.File('extglob-match')

  sp.File('fatal-errors')

  sp.File('for-expr')

  sp.File('func-parsing')

  sp.File('glob')

  sp.File('here-doc')

  sp.File('if_')

  sp.File('introspect')

  sp.File('let')

  sp.File('loop')

  sp.File('nameref')

  sp.File('nix-idioms')

  sp.File('nocasematch-match')

  sp.File('nul-bytes')

  sp.File('osh-only')

  sp.File('parse-errors')

  sp.File('pipeline')

  sp.File('posix')

  sp.File('process-sub')

  sp.File('prompt')

  sp.File('quote')

  sp.File('redirect')

  sp.File('regex')

  sp.File('serialize')

  sp.File('sh-func')

  sp.File('smoke')

  sp.File('strict-options')

  sp.File('subshell')

  sp.File('tilde')

  sp.File('TODO-deprecate')

  sp.File('toysh')

  sp.File('toysh-posix')

  sp.File('type-compat')

  sp.File('var-op-bash')

  sp.File('var-op-len')

  sp.File('var-op-patsub')

  sp.File('var-op-slice')

  sp.File('var-op-strip')

  sp.File('var-op-test')

  sp.File('var-ref')

  sp.File('vars-bash')

  sp.File('vars-special')

  sp.File('var-sub')

  sp.File('var-sub-quote')

  sp.File('word-eval')

  sp.File('word-split')

  sp.File('xtrace')

