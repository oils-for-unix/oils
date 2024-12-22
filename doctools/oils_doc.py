#!/usr/bin/env python2
"""oils_doc.py: HTML processing for Oil documentation.

Plugins:
  ExpandLinks expands $xref, etc.
  PygmentsPlugin -- for ```python, ```sh, ```c, etc.
  HelpTopicsPlugin -- for help-index.html

  ShPromptPlugin -- understands $ echo hi, but doesn't run anything
  ShSession -- runs shell snippets and caches the output
"""
from __future__ import print_function

import cgi
import cStringIO
import re
import sys

from doctools.util import log
from lazylex import html


def RemoveComments(s):
    """Remove <!-- comments -->"""
    f = cStringIO.StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)

    pos = 0

    for tok_id, end_pos in html.ValidTokens(s):
        if tok_id == html.Comment:
            value = s[pos:end_pos]
            # doc/release-index.md has <!-- REPLACE_WITH_DATE --> etc.
            if 'REPLACE' not in value:
                out.PrintUntil(pos)
                out.SkipTo(end_pos)
        pos = end_pos

    out.PrintTheRest()
    return f.getvalue()


class _Abbrev(object):

    def __init__(self, fmt):
        self.fmt = fmt

    def __call__(self, value):
        return self.fmt % {'value': value}


_ABBREVIATIONS = {
    'xref':
    _Abbrev('/cross-ref.html?tag=%(value)s#%(value)s'),

    # alias for osh-help, for backward compatibility
    # to link to the same version

    # TODO: Remove all of these broken links!
    'help':
    _Abbrev('osh-help.html?topic=%(value)s#%(value)s'),
    'osh-help':
    _Abbrev('osh-help.html?topic=%(value)s#%(value)s'),
    'oil-help':
    _Abbrev('oil-help.html?topic=%(value)s#%(value)s'),

    # New style: one for every chapter?
    # Problem: can't use relative links here, because some are from doc/ref, and
    # some are from doc
    'chap-type-method':
    _Abbrev('chap-type-method.html?topic=%(value)s#%(value)s'),
    'chap-plugin':
    _Abbrev('chap-plugin.html?topic=%(value)s#%(value)s'),
    'chap-builtin-cmd':
    _Abbrev('chap-builtin-cmd.html?topic=%(value)s#%(value)s'),

    # for blog
    'osh-help-latest':
    _Abbrev(
        '//oilshell.org/release/latest/doc/osh-help.html?topic=%(value)s#%(value)s'
    ),
    'oil-help-latest':
    _Abbrev(
        '//oilshell.org/release/latest/doc/oil-help.html?topic=%(value)s#%(value)s'
    ),

    # For the blog
    'oils-doc':
    _Abbrev('//www.oilshell.org/release/latest/doc/%(value)s'),
    'blog-tag':
    _Abbrev('/blog/tags.html?tag=%(value)s#%(value)s'),
    'oils-commit':
    _Abbrev('https://github.com/oilshell/oil/commit/%(value)s'),
    'oils-src':
    _Abbrev('https://github.com/oilshell/oil/blob/master/%(value)s'),
    'blog-code-src':
    _Abbrev('https://github.com/oilshell/blog-code/blob/master/%(value)s'),
    'issue':
    _Abbrev('https://github.com/oilshell/oil/issues/%(value)s'),
    'wiki':
    _Abbrev('https://github.com/oilshell/oil/wiki/%(value)s'),
}

# Backward compatibility
_ABBREVIATIONS['oil-src'] = _ABBREVIATIONS['oils-src']
_ABBREVIATIONS['oil-commit'] = _ABBREVIATIONS['oils-commit']
_ABBREVIATIONS['oil-doc'] = _ABBREVIATIONS['oils-doc']

# $xref:foo
_SHORTCUT_RE = re.compile(r'\$ ([a-z\-]+) (?: : (\S+))?', re.VERBOSE)


def ExpandLinks(s):
    """Expand $xref:bash and so forth."""
    f = cStringIO.StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)

    pos = 0

    it = html.ValidTokens(s)
    while True:
        try:
            tok_id, end_pos = next(it)
        except StopIteration:
            break

        if tok_id == html.StartTag:

            tag_lexer.Reset(pos, end_pos)
            if tag_lexer.TagName() == 'a':
                open_tag_right = end_pos

                href_start, href_end = tag_lexer.GetSpanForAttrValue('href')
                if href_start == -1:
                    continue

                # TODO: Need to unescape like GetAttr()
                href = s[href_start:href_end]

                new = None
                m = _SHORTCUT_RE.match(href)
                if m:
                    abbrev_name, arg = m.groups()
                    if not arg:
                        close_tag_left, _ = html.ReadUntilEndTag(
                            it, tag_lexer, 'a')
                        arg = s[open_tag_right:close_tag_left]

                    # Hack to so we can write [Wiki Page]($wiki) and have the link look
                    # like /Wiki-Page/
                    if abbrev_name == 'wiki':
                        arg = arg.replace(' ', '-')

                    func = _ABBREVIATIONS.get(abbrev_name)
                    if not func:
                        raise RuntimeError('Invalid abbreviation %r' %
                                           abbrev_name)
                    new = func(arg)

                if new is not None:
                    out.PrintUntil(href_start)
                    f.write(cgi.escape(new))
                    out.SkipTo(href_end)

        pos = end_pos

    out.PrintTheRest()

    return f.getvalue()


class _Plugin(object):
    """
    A plugin for HighlightCode(), which modifies <pre><code> ... </code></pre>
    """

    def __init__(self, s, start_pos, end_pos):
        self.s = s
        self.start_pos = start_pos
        self.end_pos = end_pos

    def PrintHighlighted(self, out):
        raise NotImplementedError()


# Optional newline at end
_LINE_RE = re.compile(r'(.*) \n?', re.VERBOSE)

_PROMPT_LINE_RE = re.compile(
    r'''
(\S* \$)[ ]       # flush-left non-whitespace, then dollar and space is a prompt
(.*?)             # arbitrary text
(?:               # don't highlight tab completion
  (&lt;TAB&gt;)   # it's HTML escaped!!!
  .*?
)?
(?:
  [ ][ ]([#] .*)  # optionally: two spaces then a comment
)?
$
''', re.VERBOSE)

_EOL_COMMENT_RE = re.compile(
    r'''
.*?             # arbitrary text
[ ][ ]([#] .*)  # two spaces then a comment
$
''', re.VERBOSE)

_COMMENT_LINE_RE = re.compile(r'#.*')


def Lines(s, start_pos, end_pos):
    """Yields positions in s that end a line."""
    pos = start_pos
    while pos < end_pos:
        m = _LINE_RE.match(s, pos, end_pos)
        if not m:
            raise RuntimeError("Should have matched a line")
        line_end = m.end(0)

        yield line_end

        pos = line_end


class ShPromptPlugin(_Plugin):
    """Highlight shell prompts."""

    def PrintHighlighted(self, out):
        pos = self.start_pos
        for line_end in Lines(self.s, self.start_pos, self.end_pos):

            m = _COMMENT_LINE_RE.match(self.s, pos, line_end)
            if m:
                out.PrintUntil(m.start(0))
                out.Print('<span class="sh-comment">')
                out.PrintUntil(m.end(0))
                out.Print('</span>')
            else:
                m = _PROMPT_LINE_RE.match(self.s, pos, line_end)
                if m:
                    #log('MATCH %r', m.groups())

                    out.PrintUntil(m.start(1))
                    out.Print('<span class="sh-prompt">')
                    out.PrintUntil(m.end(1))
                    out.Print('</span>')

                    out.PrintUntil(m.start(2))
                    out.Print('<span class="sh-command">')
                    out.PrintUntil(m.end(2))
                    out.Print('</span>')

                    if m.group(3):
                        out.PrintUntil(m.start(3))
                        out.Print('<span class="sh-tab-complete">')
                        out.PrintUntil(m.end(3))
                        out.Print('</span>')

                    if m.group(4):
                        out.PrintUntil(m.start(4))
                        out.Print('<span class="sh-comment">')
                        out.PrintUntil(m.end(4))
                        out.Print('</span>')
                else:
                    m = _EOL_COMMENT_RE.match(self.s, pos, line_end)
                    if m:
                        out.PrintUntil(m.start(1))
                        out.Print('<span class="sh-comment">')
                        out.PrintUntil(m.end(1))
                        out.Print('</span>')

            out.PrintUntil(line_end)

            pos = line_end


class HelpTopicsPlugin(_Plugin):
    """Highlight blocks of doc/ref/toc-*.md."""

    def __init__(self, s, start_pos, end_pos, chapter, linkify_stop_col):
        _Plugin.__init__(self, s, start_pos, end_pos)
        self.chapter = chapter
        self.linkify_stop_col = linkify_stop_col

    def PrintHighlighted(self, out):
        from doctools import help_gen

        debug_out = []
        r = help_gen.TopicHtmlRenderer(self.chapter, debug_out,
                                       self.linkify_stop_col)

        pos = self.start_pos
        for line_end in Lines(self.s, self.start_pos, self.end_pos):
            # NOTE: IndexLineToHtml accepts an HTML ESCAPED line.  It's valid to just
            # add tags and leave everything alone.
            line = self.s[pos:line_end]

            html_line = r.Render(line)

            if html_line is not None:
                out.PrintUntil(pos)
                out.Print(html_line)
                out.SkipTo(line_end)

            pos = line_end

        return debug_out


class PygmentsPlugin(_Plugin):

    def __init__(self, s, start_pos, end_pos, lang):
        _Plugin.__init__(self, s, start_pos, end_pos)
        self.lang = lang

    def PrintHighlighted(self, out):
        try:
            from pygments import lexers
            from pygments import formatters
            from pygments import highlight
        except ImportError:
            log("Warning: Couldn't import pygments, so skipping syntax highlighting"
                )
            return

        # unescape before passing to pygments, which will escape
        code = html.ToText(self.s, self.start_pos, self.end_pos)

        lexer = lexers.get_lexer_by_name(self.lang)
        formatter = formatters.HtmlFormatter()

        highlighted = highlight(code, lexer, formatter)
        out.Print(highlighted)


def SimpleHighlightCode(s):
    """Simple highlighting for test/shell-vs-shell.sh."""

    f = cStringIO.StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)

    pos = 0

    it = html.ValidTokens(s)

    while True:
        try:
            tok_id, end_pos = next(it)
        except StopIteration:
            break

        if tok_id == html.StartTag:

            tag_lexer.Reset(pos, end_pos)
            if tag_lexer.TagName() == 'pre':
                pre_start_pos = pos
                pre_end_pos = end_pos

                slash_pre_right, slash_pre_right = \
                    html.ReadUntilEndTag(it, tag_lexer, 'pre')

                out.PrintUntil(pre_end_pos)

                # Using ShPromptPlugin because it does the comment highlighting we want!
                plugin = ShPromptPlugin(s, pre_start_pos, slash_pre_right)
                plugin.PrintHighlighted(out)

                out.SkipTo(slash_pre_right)

        pos = end_pos

    out.PrintTheRest()

    return f.getvalue()


CSS_CLASS_RE = re.compile(
    r'''
   language-chapter-links-
   ([a-z0-9-]+)        # chapter name
   (?:_(\d+))?      # optional linkify_stop_col
   ''', re.VERBOSE)


def HighlightCode(s, default_highlighter, debug_out=None):
    """
    Algorithm:
    1. Collect what's inside <pre><code> ...
    2. Then read lines with ShPromptPlugin.
    3. If the line looks like a shell prompt and command, highlight them with
       <span>
    """
    if debug_out is None:
        debug_out = []

    f = cStringIO.StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)

    pos = 0

    it = html.ValidTokens(s)

    while True:
        try:
            tok_id, end_pos = next(it)
        except StopIteration:
            break

        if tok_id == html.StartTag:

            tag_lexer.Reset(pos, end_pos)
            if tag_lexer.TagName() == 'pre':
                pre_start_pos = pos
                pos = end_pos

                try:
                    tok_id, end_pos = next(it)
                except StopIteration:
                    break

                tag_lexer.Reset(pos, end_pos)
                if tok_id == html.StartTag and tag_lexer.TagName() == 'code':

                    css_class = tag_lexer.GetAttr('class')
                    code_start_pos = end_pos

                    if css_class is None:
                        slash_code_left, slash_code_right = \
                            html.ReadUntilEndTag(it, tag_lexer, 'code')

                        if default_highlighter is not None:
                            # TODO: Refactor this to remove duplication with
                            # language-{sh-prompt,oil-sh} below

                            # oil-sh for compatibility
                            if default_highlighter in ('sh-prompt', 'oils-sh',
                                                       'oil-sh'):
                                out.PrintUntil(code_start_pos)

                                # Using ShPromptPlugin because it does the comment highlighting
                                # we want!
                                plugin = ShPromptPlugin(
                                    s, code_start_pos, slash_code_left)
                                plugin.PrintHighlighted(out)

                                out.SkipTo(slash_code_left)
                            else:
                                raise RuntimeError(
                                    'Unknown default highlighter %r' %
                                    default_highlighter)

                    elif css_class.startswith('language'):
                        slash_code_left, slash_code_right = \
                            html.ReadUntilEndTag(it, tag_lexer, 'code')

                        if css_class == 'language-none':
                            # Allow ```none
                            pass

                        elif css_class in ('language-sh-prompt',
                                           'language-oil-sh'):
                            # Here's we're KEEPING the original <pre><code>
                            # Print everything up to and including <pre><code language="...">
                            out.PrintUntil(code_start_pos)

                            plugin = ShPromptPlugin(s, code_start_pos,
                                                    slash_code_left)
                            plugin.PrintHighlighted(out)

                            out.SkipTo(slash_code_left)

                        elif css_class == 'language-ysh':
                            # TODO: Write an Oil syntax highlighter.
                            pass

                        elif css_class.startswith('language-chapter-links-'):
                            m = CSS_CLASS_RE.match(css_class)
                            assert m is not None, css_class

                            #log('%s GROUPS %s', css_class, m.groups())
                            chapter, num_str = m.groups()
                            if num_str is not None:
                                linkify_stop_col = int(num_str)
                            else:
                                linkify_stop_col = -1

                            out.PrintUntil(code_start_pos)

                            plugin = HelpTopicsPlugin(s, code_start_pos,
                                                      slash_code_left, chapter,
                                                      linkify_stop_col)

                            block_debug_info = plugin.PrintHighlighted(out)

                            # e.g. these are links to cmd-lang within a block in toc-ysh
                            chap_block = {
                                'to_chap': chapter,
                                'lines': block_debug_info
                            }
                            debug_out.append(chap_block)

                            out.SkipTo(slash_code_left)

                        else:  # language-*: Use Pygments
                            # We REMOVE the original <pre><code> because
                            # Pygments gives you a <pre> already

                            # We just read closing </code>, and the next one
                            # should be </pre>.
                            try:
                                tok_id, end_pos = next(it)
                            except StopIteration:
                                break
                            tag_lexer.Reset(slash_code_right, end_pos)
                            assert tok_id == html.EndTag, tok_id
                            assert tag_lexer.TagName(
                            ) == 'pre', tag_lexer.TagName()
                            slash_pre_right = end_pos

                            out.PrintUntil(pre_start_pos)

                            lang = css_class[len('language-'):]
                            plugin = PygmentsPlugin(s, code_start_pos,
                                                    slash_code_left, lang)
                            plugin.PrintHighlighted(out)

                            out.SkipTo(slash_pre_right)
                            f.write('<!-- done pygments -->\n')

        pos = end_pos

    out.PrintTheRest()

    return f.getvalue()


def ExtractCode(s, f):
    """Print code blocks to a plain text file.

    So we can at least validate the syntax.

    Similar to the algorithm code above:

    1. Collect what's inside <pre><code> ...
    2. Decode &amp; -> &,e tc. and return it
    """
    out = html.Output(s, f)
    tag_lexer = html.TagLexer(s)

    block_num = 0
    pos = 0
    it = html.ValidTokens(s)

    while True:
        try:
            tok_id, end_pos = next(it)
        except StopIteration:
            break

        if tok_id == html.StartTag:
            tag_lexer.Reset(pos, end_pos)
            if tag_lexer.TagName() == 'pre':
                pre_start_pos = pos
                pos = end_pos

                try:
                    tok_id, end_pos = next(it)
                except StopIteration:
                    break

                tag_lexer.Reset(pos, end_pos)
                if tok_id == html.StartTag and tag_lexer.TagName() == 'code':

                    css_class = tag_lexer.GetAttr('class')
                    # Skip code blocks that look like ```foo
                    # Usually we use 'oil-sh' as the default_highlighter, and
                    # all those code blocks should be extracted.  TODO: maybe
                    # this should be oil-language?
                    if css_class is None:
                        code_start_pos = end_pos

                        out.SkipTo(code_start_pos)
                        out.Print('# block %d' % block_num)
                        out.Print('\n')

                        slash_code_left, slash_code_right = \
                            html.ReadUntilEndTag(it, tag_lexer, 'code')

                        text = html.ToText(s, code_start_pos, slash_code_left)
                        out.SkipTo(slash_code_left)

                        out.Print(text)
                        out.Print('\n')

                        block_num += 1

        pos = end_pos

    #out.PrintTheRest()


class UlTableParser(object):

    def __init__(self, lexer, tag_lexer):
        self.lexer = lexer
        self.tag_lexer = tag_lexer

        self.tok_id = html.Invalid
        self.start_pos = 0
        self.end_pos = 0

    def _CurrentString(self):
        part = self.tag_lexer.s[self.start_pos:self.end_pos]
        return part

    def _Next(self):
        """
        Advance and set self.tok_id, self.start_pos, self.end_pos
        """
        self.start_pos = self.end_pos
        try:
            self.tok_id, self.end_pos = next(self.lexer)
        except StopIteration:
            raise
        if 0:
            part = self._CurrentString()
            log('[%3d - %3d] %r', self.start_pos, self.end_pos, part)

        #self.tok_id = html.EndOfStream
        # Don't change self.end_pos

    def _Eat(self, tok_id, s=None):
        """
        Advance, and assert we got the right input
        """

        # TODO:
        # - _EatTag()
        # - _EatRawData

        if self.tok_id != tok_id:
            raise html.ParseError('Expected token %s, got %s',
                                  html.TokenName(tok_id),
                                  html.TokenName(self.tok_id))
        if tok_id in (html.StartTag, html.EndTag):
            self.tag_lexer.Reset(self.start_pos, self.end_pos)
            tag_name = self.tag_lexer.TagName()
            if s is not None and s != tag_name:
                raise html.ParseError('Expected tag %r, got %r', s, tag_name)
        elif tok_id == html.RawData:
            actual = self._CurrentString()
            if s is not None and s != actual:
                raise html.ParseError('Expected data %r, got %r', s, actual)
        else:
            if s is not None:
                raise AssertionError("Don't know what to do with %r" % s)
        self._Next()

    def _WhitespaceOk(self):
        """
        Optional whitespace
        """
        if self.tok_id == html.RawData and self._CurrentString().isspace():
            self._Next()

    def FindUlTable(self):
        """Find <table ...> <ul>

        Return the START position of the <ul>
        Similar algorithm as html.ReadUntilStartTag()
        """
        tag_lexer = self.tag_lexer

        # Find first table
        while True:
            self._Next()
            if self.tok_id == html.EndOfStream:
                return -1

            tag_lexer.Reset(self.start_pos, self.end_pos)
            if (self.tok_id == html.StartTag and
                    tag_lexer.TagName() == 'table'):
                while True:
                    self._Next()
                    if self.tok_id != html.RawData:
                        break

                tag_lexer.Reset(self.start_pos, self.end_pos)
                if (self.tok_id == html.StartTag and
                        tag_lexer.TagName() == 'ul'):
                    return self.start_pos
        return -1

    def _ListItem(self):
        self._WhitespaceOk()

        if self.tok_id != html.StartTag:
            return None

        self._Eat(html.StartTag, 'li')

        left = self.start_pos

        # Any tag except end tag
        inner_html = None
        balance = 0
        while True:
            # TODO: This has to  match NESTED
            # <li> <li>foo</li> </li>
            # Because cells can have bulleted lists

            if self.tok_id == html.StartTag:
                self.tag_lexer.Reset(self.start_pos, self.end_pos)
                if self.tag_lexer.TagName() == 'li':
                    balance += 1

            if self.tok_id == html.EndTag:
                self.tag_lexer.Reset(self.start_pos, self.end_pos)
                if self.tag_lexer.TagName() == 'li':
                    balance -= 1
                    if balance < 0:
                        break
            self._Next()

        right = self.start_pos  # start of the end tag

        inner_html = self.tag_lexer.s[left:right]
        #log('RAW inner html %r', inner_html)

        #self._Eat(html.EndTag, 'li')
        self._Next()

        return inner_html

    def _ParseTHead(self):
        """
        Assume we're looking at the first <ul> tag.  Now we want to find
        <li>thead and the nested <ul>

        Grammar:

        THEAD = 
          [StartTag 'ul']
          [RawData \s*]?
          [StartTag 'li']
          [RawData thead\s*]
            [StartTag 'ul']   # Indented bullet that starts -
            LIST_ITEM+
            [RawData \s*]?
            [EndTag 'ul']
          [RawData thead\s*]
          [End 'li']

        LIST_ITEM =
          [RawData \s*]?
          [StartTag 'li']
          ANY*               # NOT context-free - anything that's not the end
                             # This is what we should capture in CELLS
          [EndTag 'li']

        Two Algorithms:

        1. Replacement:
           - skip over the first ul 'thead' li, and ul 'tr' li
           - then replace the next ul -> tr, and li -> td
        2. Parsing and Rendering:
           - parse them into a structure
           - skip all the text
           - print your own HTML

        I think the second one is better, because it allows attribute extensions
        to thead

        - thead
          - name [link][]
            - colgroup=foo align=left
          - age
            - colgroup=foo align=right
        """
        #log('*** _ParseTHead')
        cells = []

        self._WhitespaceOk()
        self._Eat(html.StartTag, 'li')

        # TODO: pass regex so it's tolerant to whitespace?
        self._Eat(html.RawData, 'thead\n')

        # This is the row data
        self._Eat(html.StartTag, 'ul')

        while True:
            inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append(inner_html)
        self._WhitespaceOk()

        self._Eat(html.EndTag, 'ul')

        self._WhitespaceOk()
        self._Eat(html.EndTag, 'li')

        #log('_ParseTHead %s ', html.TOKEN_NAMES[self.tok_id])
        return cells

    def _ParseTr(self):
        """
        Assume we're looking at the first <ul> tag.  Now we want to find
        <li>tr and the nested <ul>

        Grammar:

        TR = 
          [RawData \s*]?
          [StartTag 'li']
          [RawData thead\s*]
            [StartTag 'ul']   # Indented bullet that starts -
            LIST_ITEM+        # Defined above
            [RawData \s*]?
            [EndTag 'ul']
        """
        #log('*** _ParseTr')

        cells = []

        self._WhitespaceOk()

        # Could be a </ul>
        if self.tok_id != html.StartTag:
            return None

        self._Eat(html.StartTag, 'li')

        # TODO: pass regex so it's tolerant to whitespace?
        self._Eat(html.RawData, 'tr\n')

        # This is the row data
        self._Eat(html.StartTag, 'ul')

        while True:
            inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append(inner_html)
            # TODO: assert

        self._WhitespaceOk()

        self._Eat(html.EndTag, 'ul')

        self._WhitespaceOk()
        self._Eat(html.EndTag, 'li')

        #log('_ParseTHead %s ', html.TOKEN_NAMES[self.tok_id])
        return cells

    def ParseTable(self):
        """
        Returns a structure like this
        { 'thead': [ 'col1', 'col2' ],  # TODO: columns can have CSS attributes
          'tr': [                       # raw HTML that you surround with <td>
            [ 'cell1 html', 'cell2 html' ], 
            [ 'cell1 html', 'cell2 html' ],
          ]
        }

        Grammar:

        UL_TABLE =
          [StartTag 'ul']
          THEAD   # this this returns the number of cells, so it's NOT context
                  # free
          TR*     
          [EndTag 'ul']
        """
        table = {'tr': []}

        ul_start = self.start_pos
        self._Eat(html.StartTag, 'ul')

        thead = self._ParseTHead()
        #log('___ THEAD %s', thead)

        num_cells = len(thead)
        while True:
            tr = self._ParseTr()
            if tr is None:
                break
            if len(tr) != num_cells:
                raise html.ParseError('Expected %d cells, got %d: %s',
                                      num_cells, len(tr), tr)

            #log('___ TR %s', tr)
            table['tr'].append(tr)

        self._Eat(html.EndTag, 'ul')

        self._WhitespaceOk()

        ul_end = self.start_pos

        table['thead'] = thead
        table['ul_start'] = ul_start
        table['ul_end'] = ul_end

        if 0:
            log('table %s', table)
            from pprint import pprint
            pprint(table)

        return table


def ReplaceTables(s, debug_out=None):
    """
    ul-table: Write tables using bulleted list
    """
    if debug_out is None:
        debug_out = []

    f = cStringIO.StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)
    it = html.ValidTokens(s)

    p = UlTableParser(it, tag_lexer)

    while True:
        ul_start = p.FindUlTable()
        if ul_start == -1:
            break

        #log('UL START %d', ul_start)
        out.PrintUntil(ul_start)

        table = p.ParseTable()
        #log('UL END %d', ul_end)

        # Don't write the matching </u> of the LAST row, but write everything
        # after that
        out.SkipTo(table['ul_end'])

        # Now write the table
        out.Print('<thead>\n')
        out.Print('<tr>\n')
        for cell in table['thead']:
            # TODO: parse <ulcol> and print attributes <td> attributes
            out.Print('  <td>')
            out.Print(cell)
            out.Print('</td>\n')
        out.Print('</tr>\n')
        out.Print('</thead>\n')

        for row in table['tr']:
            out.Print('<tr>\n')
            for cell in row:
                out.Print('  <td>')
                out.Print(cell)
                out.Print('</td>\n')
            out.Print('</tr>\n')

    out.PrintTheRest()

    return f.getvalue()


class ShellSession(object):
    """
    TODO: Pass this to HighlightCode as a plugin

    $ x=one
    $ echo $x
    $ echo two

    Becomes

    $ x=one
    $ echo $x
    one
    $ echo two
    two

    And then you will have
    blog/2019/12/_shell_session/
      $hash1-stdout.txt
      $hash2-stdout.txt

    It hashes the command with md5 and then brings it back.
    If the file already exists then it doesn't run it again.
    You can delete the file to redo it.

    TODO: write a loop that reads one line at a time, writes, it, then reads
    output from bash.
    Use the Lines iterator to get lines.
    For extra credit, you can solve the PS2 problem?  That's easily done with
    Oil's parser.
    """

    def __init__(self, shell_exe, cache_dir):
        """
        Args:
          shell_exe: sh, bash, osh, or oil.  Use the one in the $PATH by default.
          cache_dir: ~/git/oilshell/oilshell.org/blog/2019/12/session/
        """
        self.shell_exe = shell_exe
        self.cache_dir = cache_dir

    def PrintHighlighted(self, s, start_pos, end_pos, out):
        """
        Args:
          s: an HTML string.
        """
        pass


def main(argv):
    action = argv[1]

    if action == 'highlight':
        # for test/shell-vs-shell.sh

        html = sys.stdin.read()
        out = SimpleHighlightCode(html)
        print(out)

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    main(sys.argv)
