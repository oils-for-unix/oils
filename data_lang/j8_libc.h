#ifndef DATA_LANG_J8_LIBC_H
#define DATA_LANG_J8_LIBC_H

typedef struct j8_buf_t {
  unsigned char* data;
  int len;
} j8_buf_t;

// Places an encoded string in out_buf.
//
//   Caller must free the returned buffer after using it.
//   The buffer has a len, and data is NUL-terminated.  These will match
//   because encoded J8 strings can't have NUL bytes in them.
//
// Example:
//   j8_buf_t result = {0};
//   EncodeString({"foo", 3}, &result, 1);
//
//   printf("%s\n", result.data);
//   free(result.data);
//
// There are no encoding errors -- this is part of the J8 design!

void J8EncodeString(j8_buf_t in_buf, j8_buf_t* out_buf, int j8_fallback);

#define STYLE_DOLLAR_SQ 1  // $'\xff'
#define STYLE_B_STRING 2   // b'\yff'

void ShellEncodeString(j8_buf_t in_buf, j8_buf_t* out_buf, int escape_style);

#endif  // DATA_LANG_J8_LIBC_H
