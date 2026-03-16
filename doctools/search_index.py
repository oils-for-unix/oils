#!/usr/bin/env python3
'''
This tool reads in the headings on a rendered HTML doc page and produces a tree
of all headings (and their anchors) which can be used as a search index.

The output is a JSON object with the shape Node[] where the Node type is
defined as:

type Node = {
    symbol: string;
    children: Node[] | undefined;
    anchor: string;
};

Usage:

  doctools/search_index.py _release/VERSION/doc/ref/chap-builtin-func.html
'''

from html.parser import HTMLParser
import argparse
import json
import os


class FindHeadings(HTMLParser):
    def __init__(self):
        super().__init__()

        self.stack = []
        self.headings = []
        self.anchor = None
        self.heading = None

        self.title = None
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.title = ''
            self.in_title = True

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.stack.append({'tag': tag, 'id': None})
            self.heading = dict(self.stack[-1])

        # Preceding each header is a <a name='anchor-name'></a>
        # Collect these anchors as link targets
        if tag == 'a' and len(attrs) == 1 and attrs[0][0] == 'name':
            # This assumes that name is the first attribute on the <a></a>,
            # which is true for our generated HTML.
            self.anchor = attrs[0][1]

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

        if len(self.stack) > 0 and self.stack[-1]['tag'] == tag:
            self.stack.pop()

            if self.heading and 'title' in self.heading:
                self.headings.append(self.heading)
            self.heading = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data
            return

        if len(self.stack) == 0 or not self.anchor:
            return

        payload = data.strip()
        if not payload:
            return

        heading = self.heading
        if heading is None:
            return

        if 'title' in heading:
            heading['title'] = heading['title'] + ' ' + payload
        else:
            heading['title'] = payload
        heading['id'] = '#' + self.anchor

    def GetSymbols(self, relpath):
        if self.title is None:
            return []

        root_title = self.title.strip()

        symbols = []
        stack = []  # (level, node)

        for heading in self.headings:
            level = int(heading['tag'][1])
            node = {'symbol': heading['title'], 'anchor': relpath + heading['id']}

            while stack and stack[-1][0] >= level:
                stack.pop()

            if stack:
                parent = stack[-1][1]
                parent_children = parent.setdefault('children', [])
                parent_children.append(node)
            else:
                symbols.append(node)

            stack.append((level, node))

        return [{'symbol': root_title, 'children': symbols, 'anchor': relpath}]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--base-dir', type=str, help='Base directory to reference links from'
    )
    parser.add_argument('html', help='HTML file to extract headings from')

    args = parser.parse_args()

    with open(args.html) as f:
        source = f.read()

    find_headings = FindHeadings()
    find_headings.feed(source)

    relpath = os.path.relpath(args.html, start=args.base_dir)
    symbols = find_headings.GetSymbols(relpath)

    print(json.dumps(symbols))


if __name__ == '__main__':
    main()
