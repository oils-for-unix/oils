#!/usr/bin/env python2
from __future__ import print_function
"""
help_gen.py

Ideas for HTML -> ANSI converter:

- `ls`  ->  <code>ls</code>  ->  is reverse video?
- [link]()  ->  <a href="">  ->  underlined, and then add a number to the bottom?
  - could also be bright blue
- <pre> is also indented 4 spaces, like the markdown
- red X <span class="X">X</span>

- comments in code examples could be green?

What about:

- headings h1, h2, h3, h4
  - Right now cards use reverse video.  Centering didn't look great.

- <ul> - you could use a Unicode bullet here
- <ol>

Word wrapping?  troff/groff doesn't do it, but they do this weird right-justify
thing.


- maybe you could have a prefix for a linked word?
  - or use [] ?
  - [SIGTERM]
  - ^SIGTERM
  .SIGTERM
  X .SIGTERM
  X @DIRSTACK
  .for .while .if

Definition lists would be nice:
  $?   exit status
  $0   first etc.
"""

import cStringIO
import HTMLParser
import os
import pprint
import re
import sys

from doctools import html_lib
from doctools.util import log
from lazylex import html


# Sections have alphabetical characters, spaces, and '/' for I/O.  They are
# turned into anchors.
SECTION_RE = re.compile(r'''
  \s*
  \[
  ([a-zA-Z0-9 /:]+)  # colon for ysh:upgrade
  \]
''', re.VERBOSE)

TOPIC_RE = re.compile(r'''
  (X[ ])?           # optional deprecation symbol X, then a single space
  @?                  # optional @array, e.g. @BASH_SOURCE
  ([a-zA-Z0-9_\-:]+)  # e.g. osh-usage, all:oil, BASH_REMATCH
  ( [ ]\S+            # optional: single space then punctuation
    |
    \(\)              # or func()
  )?      
  ([ ][ ][ ])?        # three spaces means we should keep highlighting
''', re.VERBOSE)


def _StringToHref(s):
  # lower case to match what doctools/cmark.py does
  return s.lower().replace(' ', '-')


# HACK HACK: These happen to have 3 spaces before them! 
_NOT_A_TOPIC = ['compatible', 'egrep']

# BUGS:
# - Continuation lines: hacked with ...
# - Some X before punctuation aren't highlighted

X_LEFT_SPAN = '<span style="color: darkred">'

def IndexLineToHtml(chapter, line, debug_out):
  """Convert a line of text to HTML.

  Topics are highlighted and X made red.

  Args:
    line: RAW SPAN of HTML that is already escaped.

  Returns:
    The HTML with some tags inserted.
  """
  f = cStringIO.StringIO()
  out = html.Output(line, f)

  html_page = 'chap-%s.html' % chapter

  pos = 0 # position within line

  if line.startswith('X '):
    out.Print(X_LEFT_SPAN)
    out.PrintUntil(2)
    out.Print('</span>')
    pos = 2
  elif line.startswith('  '):
    pos = 2
  else:
    return line

  # Highlight [Section] at the start of a line.
  m = SECTION_RE.match(line, pos)
  if m:
    section_name = m.group(1)
    href = _StringToHref(section_name)

    out.PrintUntil(m.start(1))
    out.Print('<a href="%s#%s" class="level2">' % (html_page, href))
    out.PrintUntil(m.end(1))  # anchor
    out.Print('</a>')

    pos = m.end(0)  # ADVANCE
  else:
    section_name = None

  line_info = {'section': section_name, 'topics': []}
  debug_out.append(line_info)

  _WHITESPACE = re.compile(r'[ ]+')
  m = _WHITESPACE.match(line, pos)
  assert m, 'Expected whitespace %r' % line

  pos = m.end(0)

  done = False
  while not done:
    # Now just match one
    m = TOPIC_RE.match(line, pos)
    if not m or m.group(2) in _NOT_A_TOPIC:
      break

    if m.group(1):
      out.PrintUntil(m.start(1))
      out.Print(X_LEFT_SPAN)
      out.PrintUntil(m.end(1))
      out.Print('</span>')

    # The linked topic
    topic = m.group(2)
    line_info['topics'].append(topic)

    out.PrintUntil(m.start(2))
    out.Print('<a href="%s#%s">' % (html_page, topic))
    out.PrintUntil(m.end(2))
    out.Print('</a>')

    # Trailing 3 spaces required to continue.
    if not m.group(4):
      done = True

    pos = m.end(0)

  out.PrintTheRest()

  return f.getvalue()


class Splitter(HTMLParser.HTMLParser):
  """Split an HTML stream starting at each of the heading tags.

  For *-help.html.
  
  TODO: Rewrite with this with lazylex!

  Algorithm:
  - ExtractBody() first, then match balanced tags
  - SPLIT by h2, h3, h4
  - Match <pre><code> blocks and re-indent
  - Later:
    - links <a href="">
    - `` is turned into inline <code></code>
    - ** ** for bold
    - * * for emphasis
    - <p> needs word wrapping!  Oops.
      - actually cmark seems to preserve this?  OK maybe not.
      - we just need space between <p>
  """
  def __init__(self, heading_tags, out):
    HTMLParser.HTMLParser.__init__(self)
    self.heading_tags = heading_tags
    self.out = out

    self.cur_group = None  # type: List[Tuple[str, str, List, List]]
    self.in_heading = False

    self.indent = 0

  def log(self, msg, *args):
    ind = self.indent * ' '
    if 0:
      log(ind + msg, *args)

  def handle_starttag(self, tag, attrs):
    if tag in self.heading_tags:
      self.in_heading = True
      if self.cur_group:
        self.out.append(self.cur_group)

      self.cur_group = (tag, attrs, [], [])

    self.log('[%d] <> %s %s', self.indent, tag, attrs)
    self.indent += 1

  def handle_endtag(self, tag):
    if tag in self.heading_tags:
      self.in_heading = False

    self.log('[%d] </> %s', self.indent, tag)
    self.indent -= 1

  def handle_entityref(self, name):
    """
    From Python docs:
    This method is called to process a named character reference of the form
    &name; (e.g. &gt;), where name is a general entity reference (e.g. 'gt').
    """
    c = html.CHAR_ENTITY[name]
    if self.in_heading:
      self.cur_group[2].append(c)
    else:
      if self.cur_group:
        self.cur_group[3].append(c)

  def handle_data(self, data):
    self.log('data %r', data)
    if self.in_heading:
      self.cur_group[2].append(data)
    else:
      if self.cur_group:
        self.cur_group[3].append(data)

  def end(self):
    if self.cur_group:
      self.out.append(self.cur_group)

    # Maybe detect nesting?
    if self.indent != 0:
      raise RuntimeError(
          'Unbalanced HTML tags: indent=%d, cur_group=%s' % (
          self.indent, self.cur_group))


def ExtractBody(s):
  """Extract what's in between <body></body>

  The splitter needs balanced tags, and what's in <head> isn't balanced.
  """
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
      if tag_lexer.TagName() == 'body':
        body_start_right = end_pos  # right after <body>

        out.SkipTo(body_start_right)
        body_end_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'body')

        out.PrintUntil(body_end_left)
        break

    pos = end_pos

  return f.getvalue()


def SplitIntoCards(heading_tags, contents):
  contents = ExtractBody(contents)

  groups = []
  sp = Splitter(heading_tags, groups)
  sp.feed(contents)
  sp.end()

  for tag, attrs, heading_parts, parts in groups:
    heading = ''.join(heading_parts).strip()

    # Don't strip leading space?
    text = ''.join(parts)
    text = text.strip('\n') + '\n'

    #log('text = %r', text[:10])

    yield tag, attrs, heading, text

  #log('make_help.py: Parsed %d parts', len(groups))


def HelpTopics(s):
  """
  Given an HTML page like index-{osh,ysh}.html,

  Yield groups (section_id, section_name, block of text)
  """
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
      #log('%r', tag_lexer.TagString())
      #log('%r', tag_lexer.TagName())

      # Capture <h2 id="foo"> first
      if tag_lexer.TagName() == 'h2':
        h2_start_right = end_pos

        open_tag_right = end_pos
        section_id  = tag_lexer.GetAttr('id')
        assert section_id, 'Expected id= in %r' % tag_lexer.TagString()

        h2_end_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'h2')

        anchor_html = s[h2_start_right : h2_end_left]
        paren_pos = anchor_html.find('(')
        if paren_pos == -1:
          section_name = anchor_html
        else:
          section_name = anchor_html[: paren_pos].strip()

        # Now find the <code></code> span
        _, code_start_right = html.ReadUntilStartTag(it, tag_lexer, 'code')
        css_class = tag_lexer.GetAttr('class') 
        assert css_class.startswith('language-chapter-links-'), tag_lexer.TagString()

        code_end_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'code')

        text = html.ToText(s, code_start_right, code_end_left)
        yield section_id, section_name, text

    pos = end_pos


class DocNode(object):
  """To visualize doc structure."""

  def __init__(self, name, attrs=None):
    self.name = name
    self.attrs = attrs  # for h2 and h3 links
    self.children = []


def CardsFromIndex(sh, out_prefix):
  sections = []
  for section_id, section_name, text in HelpTopics(sys.stdin.read()):
    if 0:
      log('section_id = %r', section_id)
      log('section_name = %r', section_name)
      log('')
      #log('text = %r', text[:20])

    topic = '%s-%s' % (sh, section_id)  # e.g. ysh-overview

    path = os.path.join(out_prefix, topic)
    with open(path, 'w') as f:
      f.write('%s\n\n' % section_name)  # section_id is printed dynamically
      f.write(text)
      #f.write('\n')  # extra
    log('  Wrote %s', path)
    sections.append(section_id)

  log('  (doctools/make_help) -> %d sections -> %s', len(sections), out_prefix)


def CardsFromChapters(out_dir, tag_level, paths):
  # TODO:
  # - we only need a few fixed cards
  # - turn this into a dict with sections
  topics = {}

  root_node = DocNode('/')
  cur_h2_node = None

  seen = set()
  for path in paths:
    with open(path) as f:
      contents = f.read()

    filename = os.path.basename(path)

    tmp, _ = os.path.splitext(filename)
    assert tmp.startswith('chap-')
    chapter_name = tmp[len('chap-'):]

    page_node = DocNode(filename)

    cards = SplitIntoCards(['h2', 'h3', 'h4'], contents)

    for tag, attrs, heading, text in cards:
      values = [v for k, v in attrs if k == 'id']
      id_value = values[0] if len(values) == 1 else None

      topic_id = id_value if id_value else heading.replace(' ', '-')

      if tag == 'h2':
        h2 = DocNode(heading, attrs=attrs)
        page_node.children.append(h2)
        cur_h2_node = h2
      elif tag == 'h3':
        h3 = DocNode(heading, attrs=attrs)
        cur_h2_node.children.append(h3)

      if tag != tag_level:
        continue  # we only care about h3 now

      if 0:
        log('tag = %r', tag)
        log('topic_id = %r', topic_id)
        log('heading = %r', heading)
        log('text = %r', text[:20])

      embed = ('oils-embed', '1') in attrs

      if out_dir is not None and embed:
        # indices start with _
        path = os.path.join(out_dir, topic_id)
        with open(path, 'w') as f:
          f.write(text)

      # help builtin will show URL if there's a chapter name
      topics[topic_id] = None if embed else chapter_name

      if topic_id in seen:
        log('Warning: %r is a duplicate topic', topic_id)
      seen.add(topic_id)

    root_node.children.append(page_node)

  # 89 sections, 257 topics/cards
  # Also want stats about which ones are done
  num_sections = sum(len(child.children) for child in root_node.children)

  log('%d chapters -> (doctools/make_help) -> %d <h3> cards from %d <h2> sections to %s',
      len(paths), len(topics), num_sections, out_dir)

  return topics, root_node


class StrPool(object):
  def __init__(self):
    self.var_names = {}
    self.global_strs = []
    self.unique_id = 1

  def Add(self, s):
    if s in self.var_names:
      return

    var_name = 'gStr%d' % self.unique_id
    self.unique_id += 1

    import json
    # Use JSON as approximation for C++ string
    self.global_strs.append('GLOBAL_STR(%s, %s)' % (var_name, json.dumps(s)))

    self.var_names[s] = var_name


def WriteTopicDict(topic_dict, header_f, cc_f):
  header_f.write('''
#include "mycpp/runtime.h"

namespace help_meta {
Dict<Str*, Str*>* TopicMetadata();
}
''')

  pool = StrPool()

  for k, v in topic_dict.iteritems():
    pool.Add(k)
    if v is not None:
      pool.Add(v)
    #log('%s %s', k, v)

  num_items = len(topic_dict)
  key_names = []
  val_names = []

  for k, v in topic_dict.iteritems():
    key_names.append(pool.var_names[k])
    if v is None:
      v_str = 'nullptr'
    else:
      v_str = pool.var_names[v]
    val_names.append(v_str)

  cc_f.write('''
#include "mycpp/runtime.h"

namespace help_meta {

%s

GLOBAL_DICT(gTopics, Str*, Str*, %d, {%s}, {%s});

Dict<Str*, Str*>* TopicMetadata() {
  return gTopics;
}
}
''' % ('\n'.join(pool.global_strs), num_items, ' COMMA '.join(key_names),
       ' COMMA '.join(val_names)))


def main(argv):
  action = argv[1]

  if action == 'cards-from-index':
    sh = argv[2]  # osh or ysh
    out_prefix = argv[3]

    # Read HTML from stdin
    # TODO: could pass a list of files to speed it up
    CardsFromIndex(sh, out_prefix)

  elif action == 'cards-from-chapters':

    out_dir = argv[2]
    py_out = argv[3]
    cc_prefix = argv[4]
    pages = argv[5:]

    topic_dict, debug_info = CardsFromChapters(out_dir, 'h3', pages)

    # Write topic dict as Python and C++

    with open(py_out, 'w') as f:
      f.write('TOPICS = %s\n' % pprint.pformat(topic_dict))

      f.write('''

from typing import Dict

def TopicMetadata():
  # type: () -> Dict[str, str]
  return TOPICS
''')

    h_path = cc_prefix + '.h'
    cc_path = cc_prefix + '.cc'

    with open(h_path, 'w') as header_f:
      with open(cc_path, 'w') as cc_f:
        WriteTopicDict(topic_dict, header_f, cc_f)

  elif action == 'ref-check':
    from doctools import cmark
    from doctools import oil_doc
    from doctools import ref_check

    chapters = []
    index_debug_info = []

    for path in argv[2:]:
      filename = os.path.basename(path)

      if filename.endswith('.md'):
        assert filename.startswith('index-'), path

        # First convert to HTML
        with open(path) as in_file:
          html = cmark.md2html(in_file.read())

        # Now highlight code, which # which gives debug output for the
        # language-chapter-links-*
        html = oil_doc.HighlightCode(html, None,
                                     debug_out=index_debug_info)

      elif filename.endswith('.html'):
        assert filename.startswith('chap-'), path

        # . CardsFromChapters() on chap-*, which gives you debug_Info above
        chapters.append(path)

      else:
        raise RuntimeError('Expected index-* or chap-*, got %r' % filename)

    # out_dir=None so we don't write anything
    topics, chap_tree = CardsFromChapters(None, 'h3', chapters)
    #print(topics)

    ref_check.Check(index_debug_info, chap_tree)


    # TODO: check all docs
    # 3. Ref Check

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)


# vim: sw=2
