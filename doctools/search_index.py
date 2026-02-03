#!/usr/bin/env python3

# This tool reads in the headings on a doc/ref page and produces a list of all
# the symbols (and their anchors) which can be used as a search index.
#
# Currently a WIP.
#
# Usage:
#
#  doctools/search_index.py _release/VERSION/doc/ref/chap-builtin-func.html

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

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.title = ''

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.stack.append({ 'tag': tag, 'id': None })
            self.heading = dict(self.stack[-1])

        # Preceding each header is a <a name="anchor-name"></a>
        # Collect these anchors as link targets
        if tag in 'a' and len(attrs) == 1 and attrs[0][0] == 'name':
            # Note: attrs is a list [('prop1', 'value'), ('prop2', 'value')]
            self.anchor = attrs[0][1]

    def handle_endtag(self, tag):
        if len(self.stack) > 0 and self.stack[-1]['tag'] == tag:
            self.stack.pop()

            # Some headers are empty
            if 'title' in self.heading:
                self.headings.append(self.heading)
            self.heading = None

    def handle_data(self, data):
        if self.title == '':
            self.title = data

        # Ignore data outside of headers
        if len(self.stack) == 0:
            return

        # We have to drop headers without anchors
        if not self.anchor:
            return

        data = data.strip()
        if not data:
            # Some headers are empty
            return

        if 'title' in self.heading:
            self.heading['title'] = self.heading['title'] + ' ' + data
        else:
            self.heading['title'] = data
        self.heading['id'] = '#' + self.anchor

    def get_symbols(self, relpath: str):
        symbol = None
        symbols = []

        if not self.title:
            return []

        for heading in self.headings:
            symbol = heading['title']
            if heading['tag'] == 'h2':
                symbols.append({ 'symbol': symbol, 'children': [], 'anchor': relpath + heading['id'] })
            elif heading['tag'] == 'h3':
                symbols[-1]['children'].append({ 'symbol': symbol, 'anchor': relpath + heading['id'] })

        # Trim empty children lists to save space (saves ~4kB at time of writing)
        for item in symbols:
            if len(item['children']) == 0:
                del item['children']

        return [{ 'symbol': self.title, 'children': symbols, 'anchor': relpath }]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-dir', type=str, help='Base directory to reference links from')
    parser.add_argument('html', help='HTML file to extract headings from')

    args = parser.parse_args()

    with open(args.html) as f:
        source = f.read()

    find_headings = FindHeadings()
    find_headings.feed(source)

    relpath = os.path.relpath(args.html, start=args.base_dir)
    symbols = find_headings.get_symbols(relpath)

    print(json.dumps(symbols))


if __name__ == '__main__':
    main()
