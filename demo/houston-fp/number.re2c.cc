// re2c $INPUT -o $OUTPUT -i --case-ranges
#include <assert.h>
#include <stdio.h>

bool lex(const char *s) {
    const char *YYCURSOR = s;
    /*!re2c
        re2c:yyfill:enable = 0;
        re2c:define:YYCTYPE = char;

        number = [1-9][0-9]*;

        number { return true; }
        *      { return false; }
    */
}

int main(int argc, char** argv) {
    const char *s = argv[1];
    bool matched = lex(s);
    printf("%d %s\n", matched, s);
}
