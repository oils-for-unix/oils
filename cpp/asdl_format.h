// asdl_format.h

#ifndef ASDL_FORMAT_H
#define ASDL_FORMAT_H

#include "hnode_asdl.h"
#include "mylib.h"

namespace format {

// COPIED by hand from the asdl/runtime.cc translation.
// gen_cpp_test.cc needs this.

class ColorOutput {
 public:
  ColorOutput(mylib::Writer* f);
  virtual format::ColorOutput* NewTempBuffer();
  virtual void FileHeader();
  virtual void FileFooter();
  virtual void PushColor(hnode_asdl::color_t e_color);
  virtual void PopColor();
  virtual void write(Str* s);
  void WriteRaw(Tuple2<Str*, int>* raw);
  int NumChars();
  Tuple2<Str*, int> GetRaw();

  mylib::Writer* f;
  int num_chars;
};

class TextOutput : public ColorOutput {
 public:
  TextOutput(mylib::Writer* f);
  virtual format::TextOutput* NewTempBuffer();
  virtual void PushColor(hnode_asdl::color_t e_color);
  virtual void PopColor();
};

void PrintTree(hnode_asdl::hnode_t* node, format::ColorOutput* f);

}  // namespace format

#endif  // ASDL_FORMAT_H
