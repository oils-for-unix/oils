#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Misc builtins."""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import loc_t
from core import pyos
from core import pyutil
from core import util
from core import vm
from frontend import flag_util
from mycpp import mylib
from mycpp.mylib import log

from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from core.pyutil import _ResourceLoader
    from display import ui

_ = log


class Times(vm._Builtin):

    def __init__(self):
        # type: () -> None
        vm._Builtin.__init__(self)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        pyos.PrintTimes()
        return 0


# Needs a different _ResourceLoader to translate
class Help(vm._Builtin):

    def __init__(self, lang, loader, help_data, errfmt):
        # type: (str, _ResourceLoader, Dict[str, str], ui.ErrorFormatter) -> None
        self.lang = lang
        self.loader = loader
        self.help_data = help_data
        self.errfmt = errfmt
        self.version_str = pyutil.GetVersion(self.loader)
        self.f = mylib.Stdout()

    def _ShowTopic(self, topic_id, blame_loc):
        # type: (str, loc_t) -> int

        prefix = 'https://www.oilshell.org/release'

        # For local preview
        if 0:
            prefix = 'file:///home/andy/git/oilshell/oil/_release'
            self.version_str = 'VERSION'

        chapter_name = self.help_data.get(topic_id)

        # If we have a chapter name, it's not embedded in the binary.  So just
        # print the URL.
        if chapter_name is not None:
            util.PrintTopicHeader(topic_id, self.f)
            print('    %s/%s/doc/ref/chap-%s.html#%s' %
                  (prefix, self.version_str, chapter_name, topic_id))
            return 0

        found = util.PrintEmbeddedHelp(self.loader, topic_id, self.f)
        if not found:
            # Notes:
            # 1. bash suggests:
            # man -k zzz
            # info zzz
            # help help
            # We should do something smarter.

            # 2. This also happens on 'build/dev.sh minimal', which isn't quite
            # accurate.  We don't have an exact list of help topics!

            # 3. This is mostly an interactive command.  Is it obnoxious to
            # quote the line of code?
            self.errfmt.Print_('no help topics match %r' % topic_id, blame_loc)
            return 1

        return 0

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        attrs, arg_r = flag_util.ParseCmdVal('help', cmd_val)
        #arg = arg_types.help(attrs.attrs)

        topic_id, blame_loc = arg_r.Peek2()
        if topic_id is None:
            found = self._ShowTopic('help', blame_loc) == 0
            assert found

            # e.g. ysh-chapters
            found = self._ShowTopic('%s-chapters' % self.lang, blame_loc) == 0
            assert found

            print('All docs: https://www.oilshell.org/release/%s/doc/' %
                  self.version_str)
            print('')

            return 0
        else:
            arg_r.Next()

        return self._ShowTopic(topic_id, blame_loc)
