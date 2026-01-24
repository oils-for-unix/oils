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


class FindHeadings(HTMLParser):
    def __init__(self):
        super().__init__()

        self.stack = []
        self.headings = []

    def handle_starttag(self, tag, attrs):
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.stack.append({ 'tag': tag, 'id': None })

    def handle_endtag(self, tag):
        if len(self.stack) > 0 and self.stack[-1]['tag'] == tag:
            self.stack.pop()

    def handle_data(self, data):
        if len(self.stack) == 0:
            return

        heading = dict(self.stack[-1])
        heading['title'] = data
        heading['id'] = '#' + data
        self.headings.append(heading)

    def get_symbols(self):
        symbol = None
        symbols = []
        for heading in self.headings:
            if heading['tag'] == 'h2':
                symbol = heading['title']
                symbols.append({ 'symbol': symbol, 'anchor': heading['id'] })
            elif heading['tag'] == 'h3':
                symbols.append({ 'symbol': symbol + ' > ' + heading['title'], 'anchor': heading['id'] })

        return symbols


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('html')

    args = parser.parse_args()

    with open(args.html) as f:
        source = f.read()

    find_headings = FindHeadings()
    find_headings.feed(source)

    print('\n'.join([sym['symbol'] + '  <--  ' + args.html + sym['anchor'] for sym in find_headings.get_symbols()]))
    #for level, heading in find_headings.headings:
    #    print(level, heading)


if __name__ == '__main__':
    main()
