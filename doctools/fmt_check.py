#!/usr/bin/env python3
"""fmt_check.py

Check that the output HTML obeys the following rules:

 - No orphaned backticks '`' should be part of a `inline code block`
   (ie. any backticks not in a <code> block is treated as an error)
 - Lines in a <code> should be shorter than 70 chars (else they overflow)
"""

import html.parser
import sys

from doctools.util import log


class TagAwareHTMLParser(html.parser.HTMLParser):
    def __init__(self, file):
        super().__init__()
        self.tag_stack = []
        self.file = file

    def location_str(self):
        line, col = self.getpos()
        return '%s:%d:%d' % (self.file, line, col)

    def handle_starttag(self, tag, _attrs):
        # Skip self-closing elements
        if tag in ('meta', 'img'):
            return

        self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        popped = self.tag_stack.pop()
        if tag != popped:
            print('%s [WARN] Mismatched tag!' % self.location_str(),
                  'Expected </%s> but got </%s>'  % (popped, tag))

class CheckBackticks(TagAwareHTMLParser):
    def __init__(self, file):
        super().__init__(file)
        self.has_error = False

    def handle_data(self, text):
        # Ignore eg, <code> tags
        if len(self.tag_stack) and (
            self.tag_stack[-1] not in ("p", "h1", "h2", "h3", "a")):
            return

        idx = text.find('`')
        if idx == -1:
            return

        print('%s [ERROR] Found stray backtick %r' % (self.location_str(), text))

        self.has_error = True


class CheckCodeLines(TagAwareHTMLParser):
    # Found when the display is 801px in width
    MAX_LINE_LENGTH = 70

    def __init__(self, file):
        super().__init__(file)
        self.has_error = False

    def handle_data(self, text):
        # Ignore eg, <code> tags
        if len(self.tag_stack) and self.tag_stack[-1] != 'code':
            return

        for i, line in enumerate(text.splitlines()):
            if len(line) > self.MAX_LINE_LENGTH:
                print('%s [ERROR] Line %d of <code> is too long: %r' % (self.location_str(), i + 1, line))
                self.has_error = True


def FormatCheck(filename):
    backticks = CheckBackticks(filename)
    with open(filename, "r") as f:
        backticks.feed(f.read())

    lines = CheckCodeLines(filename)
    with open(filename, "r") as f:
        lines.feed(f.read())

    return backticks.has_error or lines.has_error

def main(argv):
    action = argv[1]

    any_error = False
    for path in argv[1:]:
        if not path.endswith('.html'):
            raise RuntimeError('Expected %r to be a .html file' % filename)

        this_error = FormatCheck(path)
        any_error = any_error or this_error
        log("%s %s" % ("ER" if this_error else "OK", path))

    if any_error:
        raise RuntimeError("Formatting errors found")


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
