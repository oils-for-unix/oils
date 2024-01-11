#ifndef DATA_LANG_J8C_H
#define DATA_LANG_J8C_H

typedef struct j8_buf_t {
  unsigned char* data;
  int len;
} j8_buf_t;

// Returns an encoded string.
//
//   Caller must free the returned buffer after using it
//
//   j8_buf_t result;
//   EncodeString({"foo", 3}, &result, 1);
//   printf("%s\n", result.data);
//   free(result.data);
//
// There are no encoding errors -- this is part of the J8 design!

void EncodeString(j8_buf_t in_buf, j8_buf_t* out_buf, int j8_fallback);

#endif  // DATA_LANG_J8C_H
