"""
j8_lite.py: Low dependency library for ASDL circular dep in prebuilt/
"""

import fastfunc  # Skip pyj8 and fastlex

def EncodeString(s, unquoted_ok=False):
    # type: (str, bool) -> str
    """Convenience API that doesn't require instance of j8.Printer()

    This is the same logic as j8.Printer.EncodeString(), which reuses a
    BufWriter.

    If you have to create many strings, it may generate less garbage to use
    that method, then call BufWriter.clear() in between.
    """
    if unquoted_ok and fastfunc.CanOmitQuotes(s):
        return s

    return fastfunc.J8EncodeString(s, 1)  # j8_fallback is true
