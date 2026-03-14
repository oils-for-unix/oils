#!/usr/bin/env python2
"""
invalid_ctx_name.py
"""
from typing import Any


class ShouldStartWithCtx(object):

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        pass
