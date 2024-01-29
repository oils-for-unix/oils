#include "data_lang/j8_libc.h"

#include <stdbool.h>  // false
#include <stdlib.h>   // realloc

#include "data_lang/j8.h"  // EncodeRuneOrByte

void EncodeBString(j8_buf_t in_buf, j8_buf_t* out_buf, int capacity) {
  // Compute pointers for the inner loop
  unsigned char* in = (unsigned char*)in_buf.data;
  unsigned char* in_end = in + in_buf.len;

  unsigned char* out = out_buf->data;  // mutated
  unsigned char* out_end = out_buf->data + capacity;
  unsigned char** p_out = &out;

  J8_OUT('b');  // Left quote b''
  J8_OUT('\'');

  while (true) {
    // printf("B iter %p < %p and %p < %p < %p\n", in, in_end, out_buf->data,
    // out, out_end);
    J8EncodeChunk(&in, in_end, &out, out_end, true);  // Fill as much as we can
    out_buf->len = out - out_buf->data;               // recompute length

    if (in >= in_end) {
      break;
    }

    // Same growth policy as below
    capacity = capacity * 3 / 2;
    // printf("[2] new capacity %d\n", capacity);
    out_buf->data = (unsigned char*)realloc(out_buf->data, capacity);

    // Recompute pointers
    out = out_buf->data + out_buf->len;
    out_end = out_buf->data + capacity;
    p_out = &out;
  }

  J8_OUT('\'');
  out_buf->len = out - out_buf->data;

  J8_OUT('\0');  // NUL terminate for printf
}

// $'' escaping
// This function is a COPY of EncodeBString() above
void EncodeBashDollarString(j8_buf_t in_buf, j8_buf_t* out_buf, int capacity) {
  // Compute pointers for the inner loop
  unsigned char* in = (unsigned char*)in_buf.data;
  unsigned char* in_end = in + in_buf.len;

  unsigned char* out = out_buf->data;  // mutated
  unsigned char* out_end = out_buf->data + capacity;
  unsigned char** p_out = &out;

  J8_OUT('$');  // Left quote b''
  J8_OUT('\'');

  while (true) {
    // printf("B iter %p < %p and %p < %p < %p\n", in, in_end, out_buf->data,
    // out, out_end);
    // Fill as much as we can
    ShellEncodeChunk(&in, in_end, &out, out_end, STYLE_DOLLAR_SQ);
    out_buf->len = out - out_buf->data;  // recompute length

    if (in >= in_end) {
      break;
    }

    // Same growth policy as below
    capacity = capacity * 3 / 2;
    // printf("[2] new capacity %d\n", capacity);
    out_buf->data = (unsigned char*)realloc(out_buf->data, capacity);

    // Recompute pointers
    out = out_buf->data + out_buf->len;
    out_end = out_buf->data + capacity;
    p_out = &out;
  }

  J8_OUT('\'');
  out_buf->len = out - out_buf->data;

  J8_OUT('\0');  // NUL terminate for printf
}

void J8EncodeString(j8_buf_t in_buf, j8_buf_t* out_buf, int j8_fallback) {
  unsigned char* in = (unsigned char*)in_buf.data;
  unsigned char* in_end = in + in_buf.len;

  // Growth policy: Start at a fixed size min(N + 3 + 2, 16)
  int capacity = in_buf.len + 3 + 2;  // 3 for quotes, 2 potential \" \n
  if (capacity < 16) {                // account for J8_MAX_BYTES_PER_INPUT_BYTE
    capacity = 16;
  }
  // printf("[1] capacity %d j8_fallback %d\n", capacity, j8_fallback);

  out_buf->data = (unsigned char*)malloc(capacity);
  out_buf->len = 0;  // starts out empty

  unsigned char* out = out_buf->data;  // mutated
  unsigned char* out_end = out_buf->data + capacity;
  unsigned char** p_out = &out;

  J8_OUT('"');

  while (true) {
    // Fill in as much as we can
    // printf("J8 iter %p < %p and %p < %p < %p\n", in, in_end, out_buf->data,
    // out, out_end);
    int invalid_utf8 = J8EncodeChunk(&in, in_end, &out, out_end, false);
    if (invalid_utf8 && j8_fallback) {
      out_buf->len = 0;  // rewind to begining
      // printf("out %p out_end %p capacity %d\n", out, out_end, capacity);
      EncodeBString(in_buf, out_buf, capacity);  // fall back to b''
      // printf("len %d\n", out_buf->len);
      return;
    }
    out_buf->len = out - out_buf->data;  // recompute length
    // printf("[1] len %d\n", out_buf->len);

    if (in >= in_end) {
      break;
    }

    // Growth policy: every time through the loop, increase 1.5x
    //
    // The worst blowup is 6x, and 1.5 ** 5 > 6, so it will take 5 reallocs.
    // This seems like a reasonable tradeoff between over-allocating and too
    // many realloc().
    capacity = capacity * 3 / 2;
    // printf("[1] new capacity %d\n", capacity);
    out_buf->data = (unsigned char*)realloc(out_buf->data, capacity);

    // Recompute pointers
    out = out_buf->data + out_buf->len;
    out_end = out_buf->data + capacity;
    p_out = &out;
    // printf("[1] out %p out_end %p\n", out, out_end);
  }

  J8_OUT('"');
  out_buf->len = out - out_buf->data;

  J8_OUT('\0');  // NUL terminate for printf
}

// Start with '', but fall back on $'' for ASCII control and \'
//
// Depending on options, fall back to
//
// EncodeBashDollarString() -- $'\xff'
// EncodeBString()          -- b'\yff'

// Mostly a COPY of the above
void ShellEncodeString(j8_buf_t in_buf, j8_buf_t* out_buf, int escape_style) {
  unsigned char* in = (unsigned char*)in_buf.data;
  unsigned char* in_end = in + in_buf.len;

  // Growth policy: Start at a fixed size min(N + 3 + 2, 16)
  int capacity = in_buf.len + 3 + 2;  // 3 for quotes, 2 potential \" \n
  if (capacity < 16) {                // account for J8_MAX_BYTES_PER_INPUT_BYTE
    capacity = 16;
  }
  // printf("[1] capacity %d j8_fallback %d\n", capacity, j8_fallback);

  out_buf->data = (unsigned char*)malloc(capacity);
  out_buf->len = 0;  // starts out empty

  unsigned char* out = out_buf->data;  // mutated
  unsigned char* out_end = out_buf->data + capacity;
  unsigned char** p_out = &out;

  J8_OUT('"');

  while (true) {
    // Fill in as much as we can
    // printf("J8 iter %p < %p and %p < %p < %p\n", in, in_end, out_buf->data,
    // out, out_end);
    int cannot_encode = ShellEncodeChunk(&in, in_end, &out, out_end, STYLE_SQ);
    if (cannot_encode) {
      out_buf->len = 0;  // rewind to begining
      // printf("out %p out_end %p capacity %d\n", out, out_end, capacity);
      if (escape_style == STYLE_DOLLAR_SQ) {
        EncodeBashDollarString(in_buf, out_buf, capacity);  // fall back to $''
      } else {
        EncodeBString(in_buf, out_buf, capacity);  // fall back to b''
      }
      // printf("len %d\n", out_buf->len);
      return;
    }
    out_buf->len = out - out_buf->data;  // recompute length
    // printf("[1] len %d\n", out_buf->len);

    if (in >= in_end) {
      break;
    }

    // Growth policy: every time through the loop, increase 1.5x
    //
    // The worst blowup is 6x, and 1.5 ** 5 > 6, so it will take 5 reallocs.
    // This seems like a reasonable tradeoff between over-allocating and too
    // many realloc().
    capacity = capacity * 3 / 2;
    // printf("[1] new capacity %d\n", capacity);
    out_buf->data = (unsigned char*)realloc(out_buf->data, capacity);

    // Recompute pointers
    out = out_buf->data + out_buf->len;
    out_end = out_buf->data + capacity;
    p_out = &out;
    // printf("[1] out %p out_end %p\n", out, out_end);
  }

  J8_OUT('"');
  out_buf->len = out - out_buf->data;

  J8_OUT('\0');  // NUL terminate for printf
}
