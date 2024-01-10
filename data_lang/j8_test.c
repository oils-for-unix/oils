#include "data_lang/j8.h"

#include <string>

#include "vendor/greatest.h"

// Fixed for now
struct Buf {
  unsigned char* data;
  int capacity;
  int len;
};

void Encode(char* s, int n, Buf* buf, int is_j8) {
  char* orig_s = s;  // save for rewinding

  unsigned char* in = (unsigned char*)s;
  unsigned char* input_end = (unsigned char*)s + n;

  unsigned char* out = buf->data;       // mutated
  unsigned char* orig_out = buf->data;  // not mutated

  unsigned char** p_out = &out;  // for J8_OUT()

  J8_OUT('"');
  // printf("*in %p *out %p\n", *in, *out);

  int invalid_utf8 = 0;
  while (in < input_end) {
    // printf("1 in %p *out %p\n", in, *out);

    // TODO: check *out vs. capacity and maybe grow buffer
    invalid_utf8 = EncodeRuneOrByte(&in, &out, 0);  // JSON escaping

    // Try again with J8 escaping
    if (invalid_utf8 && is_j8) {
      in = (unsigned char*)orig_s;
      out = orig_out;

      J8_OUT('b');
      J8_OUT('\'');

      // TODO: check *out vs. capacity and maybe grow buffer

      while (in < input_end) {
        // printf("2 in %p *out %p\n", in, *out);
        EncodeRuneOrByte(&in, &out, 1);  // Now with J8 escaping
      }

      J8_OUT('\'');
      buf->len = out - orig_out;
      return;
    }
  }

  J8_OUT('"');
  buf->len = out - orig_out;
}

const int kChunkSize = 8;

void EncodeBString(char* s, int n, std::string* result) {
  uint8_t* in = reinterpret_cast<uint8_t*>(s);
  uint8_t* in_end = in + n;

  result->append("b'");

  while (in < in_end) {
    // printf("in %p\n", in);

    int chunk_pos = result->size();    // current position
    result->append(kChunkSize, '\0');  // "pre-allocated" bytes to overwrite

    // Need C-style pointers to call the helper function
    uint8_t* raw_data = (uint8_t*)result->data();

    uint8_t* out = raw_data + chunk_pos;
    uint8_t* orig_out = out;

    uint8_t* out_end = raw_data + result->size();

    // printf("\tEncodeChunk JSON\n");
    EncodeChunk(&in, in_end, &out, out_end, true);

    int bytes_this_chunk = out - orig_out;
    int end_index = chunk_pos + bytes_this_chunk;
    // printf("\t  num_chunks %d\n", num_chunks);
    // printf("\t  bytes_this_chunk %d\n", bytes_this_chunk);
    // printf("\tend_index %d\n", end_index);

    result->erase(end_index, std::string::npos);
  }
  result->append("'");
}

void EncodeString(char* s, int n, std::string* result, int j8_fallback) {
  uint8_t* in = reinterpret_cast<uint8_t*>(s);
  uint8_t* in_end = in + n;

  int begin_index = result->size();  // position before writing opening quote

  result->append("\"");

  while (in < in_end) {
    // printf("in %p\n", in);

    int chunk_pos = result->size();    // current position
    result->append(kChunkSize, '\0');  // "pre-allocated" bytes to overwrite

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
    }

    int bytes_this_chunk = out - orig_out;
    int end_index = chunk_pos + bytes_this_chunk;
    // printf("\t  num_chunks %d\n", num_chunks);
    // printf("\t  bytes_this_chunk %d\n", bytes_this_chunk);
    // printf("\tend_index %d\n", end_index);

    result->erase(end_index, std::string::npos);
  }
  result->append("\"");
}

void EncodeAndPrint(char* s, int n, int j8_fallback) {
#if 0
  Buf buf = {0};
  buf.data = (unsigned char*)malloc(64);
  buf.capacity = 64;

  Encode(s, n, &buf, is_j8);
  buf.data[buf.len] = '\0';  // NUL terminate

  printf("out = %s\n", buf.data);
  free(buf.data);
#else

  std::string result;
  EncodeString(s, n, &result, j8_fallback);
  printf("out = %s\n", result.c_str());

#endif
}

TEST encode_test() {
#if 1
  char* mixed = "hi \x01 \u4000\xfe\u4001\xff\xfd ' \" new \n \\ \u03bc";
  EncodeAndPrint(mixed, strlen(mixed), 0);
  EncodeAndPrint(mixed, strlen(mixed), 1);
#endif

  char* a = "ab";
  EncodeAndPrint(a, strlen(a), 0);
  EncodeAndPrint(a, strlen(a), 1);

  char* b = "0123456789";
  EncodeAndPrint(b, strlen(b), 0);
  EncodeAndPrint(b, strlen(b), 1);

  char* u = "hi \u4000 \u03bc";
  EncodeAndPrint(u, strlen(u), 0);
  EncodeAndPrint(u, strlen(u), 1);

  // Internal NUL
  char* bin = "\x00\x01\xff";
  EncodeAndPrint(bin, 3, 0);
  EncodeAndPrint(bin, 3, 1);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(encode_test);

  GREATEST_MAIN_END();
  return 0;
}
