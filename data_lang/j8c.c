#include "data_lang/j8c.h"

#include "data_lang/j8.h"

void EncodeBString(char* in, int in_len, char** out, int* out_len,
                   int j8_fallback) {
}

void EncodeString(char* in, int in_len, char** out, int* out_len,
                  int j8_fallback) {
#if 0
  uint8_t* in = reinterpret_cast<uint8_t*>(s);
  uint8_t* in_end = in + n;

  int begin_index = result->size();  // position before writing opening quote

  result->append("\"");

  printf("\t***str len %d\n", n);

  while (in < in_end) {
    int chunk_pos = result->size();  // current position

    // Compute chunk size assuming that we'll output about 5 bytes "foo" for
    // the string foo.  Cases like \u{1f}\u{1e} blow it up by a factor of 6, in
    // which case we'll make more trips through the loop.
    int chunk_size = in_end - in + 3;  // 3 for the quotes
    // clamp it to account for tiny gaps and huge strings
    if (chunk_size < 16) {
      chunk_size = 16;
    } else if (chunk_size > 4096) {
      chunk_size = 4096;
    }
    printf("\t[1] in %p chunk %d\n", in, chunk_size);

    result->append(chunk_size, '\0');  // "pre-allocated" bytes to overwrite

    // Need C-style pointers to call the helper function
    uint8_t* raw_data = (uint8_t*)result->data();

    uint8_t* out = raw_data + chunk_pos;
    uint8_t* orig_out = out;

    uint8_t* out_end = raw_data + result->size();

    // printf("\tEncodeChunk JSON\n");
    int invalid_utf8 = EncodeChunk(&in, in_end, &out, out_end, false);
    if (invalid_utf8 && j8_fallback) {
      // printf("RETRY\n");
      result->erase(begin_index, std::string::npos);
      EncodeBString(s, n, result);  // fall back to b''
      printf("\t[1] result len %d\n", result->size());
      return;
    }

    int bytes_this_chunk = out - orig_out;
    int end_index = chunk_pos + bytes_this_chunk;
    printf("\t    bytes_this_chunk %d\n", bytes_this_chunk);
    printf("\t    end_index %d\n", end_index);

    result->erase(end_index, std::string::npos);
  }
  result->append("\"");
  printf("\t[1] result len %d\n", result->size());
#endif
}
