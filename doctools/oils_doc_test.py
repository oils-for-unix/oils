#!/usr/bin/env python2
"""oils_doc_test.py: Tests for oils_doc.py."""
from __future__ import print_function

import sys
import unittest

from doctools import oils_doc  # module under test
from lazylex import html

with open('lazylex/testdata.html') as f:
    TEST_HTML = f.read()


class OilsDocTest(unittest.TestCase):

    def testTopicCssClass(self):

        CASES = [
            ('language-chapter-links-expr-lang', True),
            ('language-chapter-links-expr-lang_56', True),
        ]

        for s, matches in CASES:
            m = oils_doc.CSS_CLASS_RE.match(s)
            print(m.groups())

    def testExpandLinks(self):
        """
    <a href=$xref:bash>bash</a>
    ->
    <a href=/cross-ref?tag=bash#bash>

    NOTE: THIs could really be done with a ref like <a.*href="(.*)">
    But we're testing it
    """
        h = oils_doc.ExpandLinks(TEST_HTML)
        self.assert_('/blog/tags.html' in h, h)

    def testShPrompt(self):
        r = oils_doc._PROMPT_LINE_RE
        line = 'oil$ ls -l&lt;TAB&gt;  # comment'
        m = r.match(line)

        if 0:
            print(m.groups())
            print(m.group(2))
            print(m.end(2))

        plugin = oils_doc.ShPromptPlugin(line, 0, len(line))
        out = html.Output(line, sys.stdout)
        plugin.PrintHighlighted(out)

    def testHighlightCode(self):
        # lazylex/testdata.html has the language-sh-prompt

        h = oils_doc.HighlightCode(TEST_HTML, None)
        self.assert_('<span class="sh-prompt">' in h, h)
        #print(h)

    def testPygmentsPlugin(self):
        # TODO: Doesn't pass on Travis because pygments isn't there
        # use virtualenv or something?
        return

        HTML = '''
<pre><code class="language-sh">
  echo hi &gt; out.txt
</code></pre>
    '''
        h = oils_doc.HighlightCode(HTML, None)

        # assert there's no double escaping
        self.assert_('hi &gt; out.txt' in h, h)
        #print(h)


if __name__ == '__main__':
    unittest.main()
