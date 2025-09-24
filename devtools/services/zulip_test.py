#!/usr/bin/env python3
"""
Test cases for Zulip markdown to CommonMark conversion.

Run with: python3 devtools/services/zulip_test.py
"""

import sys
import os
import unittest

# Add the current directory to Python path so we can import zulip
sys.path.insert(0, os.path.dirname(__file__))

from zulip import convert_zulip_to_commonmark


class TestZulipConversion(unittest.TestCase):
    """Test all types of Zulip markdown conversions."""

    def test_conversions(self):
        """Test all types of Zulip markdown conversions."""

        # Test cases: (input, expected_output)
        test_cases = [
            # Topic links
            ("Check out #**blog-ideas>My Great Post** for details.",
             "Check out [#blog-ideas > My Great Post](https://oilshell.zulipchat.com/#narrow/channel/266575-blog-ideas/topic/My.20Great.20Post) for details."
             ),

            # Stream-only links
            ("Post it in #**containers** stream.",
             "Post it in [#containers](https://oilshell.zulipchat.com/#narrow/channel/308821-containers) stream."
             ),

            # Bare URLs
            ("Visit https://oils.pub/blog/ and https://github.com/oils-for-unix/oils for more info.",
             "Visit <https://oils.pub/blog/> and <https://github.com/oils-for-unix/oils> for more info."
             ),

            # URLs already in markdown links (should not be double-wrapped)
            ("Check [this link](https://oils.pub/release/0.30.0/) for details.",
             "Check [this link](https://oils.pub/release/0.30.0/) for details."
             ),

            # Mixed content
            ("See #**oil-dev>Performance Issues** and https://oils.pub/benchmarks/",
             "See [#oil-dev > Performance Issues](https://oilshell.zulipchat.com/#narrow/channel/121539-oil-dev/topic/Performance.20Issues) and <https://oils.pub/benchmarks/>"
             ),

            # Special characters in topics
            ("Check #**language-design>What's Next?** for roadmap.",
             "Check [#language-design > What's Next?](https://oilshell.zulipchat.com/#narrow/channel/384942-language-design/topic/What.27s.20Next.3F) for roadmap."
             )
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = convert_zulip_to_commonmark(input_text)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
