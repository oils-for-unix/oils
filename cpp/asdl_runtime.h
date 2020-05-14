// Header for asdl/runtime, which is itself translated and used by ASDL code.
// Most Oil code can go in a single

#ifndef ASDL_RUNTIME_H
#define ASDL_RUNTIME_H

#include "hnode_asdl.h"
#include "mylib.h"  // Str*

namespace runtime {

hnode_asdl::hnode__Record* NewRecord(Str* node_type);
hnode_asdl::hnode__Leaf* NewLeaf(Str* s, hnode_asdl::color_t e_color);
extern Str* TRUE_STR;
extern Str* FALSE_STR;
extern int NO_SPID;

}  // namespace runtime

//
// COPIED by hand from the asdl/runtime.cc translation.
//
namespace format {

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

}

#endif  // ASDL_RUNTIME_H
