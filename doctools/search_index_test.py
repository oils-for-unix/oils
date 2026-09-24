#!/usr/bin/env python3
import unittest

from doctools.search_index import FindHeadings


class FindHeadingsTest(unittest.TestCase):
    def GetSymbols(self, input_str, filename="index.html"):
        find_headings = FindHeadings()
        find_headings.feed(input_str)
        return find_headings.GetSymbols(filename)

    def testSimple(self):
        symbols = self.GetSymbols("""
            <title>My Title</title>
            <a name="anchor1"></a>
            <h1>Heading 1</h1>

            <a name="anchor1-1"></a>
            <h2>Heading 1.1</h2>

            <a name="anchor1-1-1"></a>
            <h3>Heading 1.1.1</h3>

            <a name="anchor1-1-2"></a>
            <h3>Heading 1.1.2</h3>

            <a name="anchor2"></a>
            <h1>Heading 2</h1>

            <a name="anchor2-1"></a>
            <h2>Heading 2.1</h2>
        """)

        self.assertEqual(
            symbols,
            [
                {
                    "symbol": "My Title",
                    "children": [
                        {
                            "symbol": "Heading 1",
                            "anchor": "index.html#anchor1",
                            "children": [
                                {
                                    "symbol": "Heading 1.1",
                                    "anchor": "index.html#anchor1-1",
                                    "children": [
                                        {
                                            "symbol": "Heading 1.1.1",
                                            "anchor": "index.html#anchor1-1-1",
                                        },
                                        {
                                            "symbol": "Heading 1.1.2",
                                            "anchor": "index.html#anchor1-1-2",
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "symbol": "Heading 2",
                            "anchor": "index.html#anchor2",
                            "children": [
                                {
                                    "symbol": "Heading 2.1",
                                    "anchor": "index.html#anchor2-1",
                                }
                            ],
                        },
                    ],
                    "anchor": "index.html",
                }
            ],
        )

    def testNoTitle(self):
        # Pages without a title should be skipped from indexing
        # Redirect pages like doc/oil-help.html don't have a title (or any
        # content)

        symbols = self.GetSymbols("""
            <a name="anchor1"></a>
            <h1>Heading 1</h1>
        """)

        self.assertEqual(symbols, [])

    def testEmptyTitle(self):
        # However, empty titles are fine!

        symbols = self.GetSymbols("""
            <title></title>

            <a name="anchor1"></a>
            <h1>Heading 1</h1>
        """)

        self.assertEqual(
            symbols,
            [
                {
                    "symbol": "",
                    "children": [
                        {"symbol": "Heading 1", "anchor": "index.html#anchor1"}
                    ],
                    "anchor": "index.html",
                }
            ],
        )

    def testBadNesting(self):
        # We don't want to drop any headers, so we should gracefully handle
        # headers no wrapped in a higher heading level

        for h in ["h2", "h3"]:
            symbols = self.GetSymbols(f"""
                <title>Hello!</title>

                <a name="anchor"></a>
                <{h}>Sub-heading</{h}>
            """)

            self.assertEqual(
                symbols,
                [
                    {
                        "symbol": "Hello!",
                        "children": [
                            {"symbol": "Sub-heading", "anchor": "index.html#anchor"}
                        ],
                        "anchor": "index.html",
                    }
                ],
            )

    def testComplexHeading(self):
        # Some headings have formatting. This is ignored, but we still extract all the text.

        symbols = self.GetSymbols(f"""
            <title>Title</title>

            <a name="anchor"></a>
            <h2><b>Some</b> Heading</h2>
        """)

        self.assertEqual(
            symbols,
            [
                {
                    "symbol": "Title",
                    "children": [
                        {"symbol": "Some Heading", "anchor": "index.html#anchor"}
                    ],
                    "anchor": "index.html",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
