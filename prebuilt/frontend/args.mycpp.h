// prebuilt/frontend/args.mycpp.h: GENERATED by mycpp

#ifndef FRONTEND_ARGS_MYCPP_H
#define FRONTEND_ARGS_MYCPP_H

#include "_gen/asdl/hnode.asdl.h"
#include "_gen/display/pretty.asdl.h"
#include "cpp/data_lang.h"
#include "mycpp/runtime.h"

#include "_gen/core/runtime.asdl.h"
#include "_gen/core/value.asdl.h"
#include "_gen/display/pretty.asdl.h"
#include "_gen/frontend/syntax.asdl.h"
#include "cpp/frontend_flag_spec.h"

using value_asdl::value;  // This is a bit ad hoc
using pretty_asdl::doc;

namespace runtime {  // forward declare

  class TraversalState;

}  // forward declare namespace runtime

namespace format {  // forward declare

  class ColorOutput;
  class TextOutput;
  class HtmlOutput;
  class AnsiOutput;
  class _PrettyPrinter;

}  // forward declare namespace format

namespace args {  // forward declare

  class _Attributes;
  class Reader;
  class _Action;
  class _ArgAction;
  class SetToInt;
  class SetToFloat;
  class SetToString;
  class SetAttachedBool;
  class SetToTrue;
  class SetOption;
  class SetNamedOption;
  class SetAction;
  class SetNamedAction;

}  // forward declare namespace args

namespace runtime {  // declare

using hnode_asdl::hnode;
extern int NO_SPID;
hnode::Record* NewRecord(BigStr* node_type);
hnode::Leaf* NewLeaf(BigStr* s, hnode_asdl::color_t e_color);
class TraversalState {
 public:
  TraversalState();
  Dict<int, bool>* seen{};
  Dict<int, int>* ref_count{};

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassScanned(2, sizeof(TraversalState));
  }

  DISALLOW_COPY_AND_ASSIGN(TraversalState)
};

extern BigStr* TRUE_STR;
extern BigStr* FALSE_STR;

}  // declare namespace runtime

namespace format {  // declare

using hnode_asdl::hnode;
format::ColorOutput* DetectConsoleOutput(mylib::Writer* f);
class ColorOutput {
 public:
  ColorOutput(mylib::Writer* f);
  virtual format::ColorOutput* NewTempBuffer();
  virtual void FileHeader();
  virtual void FileFooter();
  virtual void PushColor(hnode_asdl::color_t e_color);
  virtual void PopColor();
  virtual void write(BigStr* s);
  void WriteRaw(Tuple2<BigStr*, int>* raw);
  int NumChars();
  Tuple2<BigStr*, int> GetRaw();
  mylib::Writer* f{};
  int num_chars{};
  
  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(ColorOutput, f));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(ColorOutput));
  }

  DISALLOW_COPY_AND_ASSIGN(ColorOutput)
};

class TextOutput : public ::format::ColorOutput {
 public:
  TextOutput(mylib::Writer* f);
  virtual format::TextOutput* NewTempBuffer();
  virtual void PushColor(hnode_asdl::color_t e_color);
  virtual void PopColor();
  
  static constexpr uint32_t field_mask() {
    return ::format::ColorOutput::field_mask();
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(TextOutput));
  }

  DISALLOW_COPY_AND_ASSIGN(TextOutput)
};

class HtmlOutput : public ::format::ColorOutput {
 public:
  HtmlOutput(mylib::Writer* f);
  virtual format::HtmlOutput* NewTempBuffer();
  virtual void FileHeader();
  virtual void FileFooter();
  virtual void PushColor(hnode_asdl::color_t e_color);
  virtual void PopColor();
  virtual void write(BigStr* s);
  
  static constexpr uint32_t field_mask() {
    return ::format::ColorOutput::field_mask();
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(HtmlOutput));
  }

  DISALLOW_COPY_AND_ASSIGN(HtmlOutput)
};

class AnsiOutput : public ::format::ColorOutput {
 public:
  AnsiOutput(mylib::Writer* f);
  virtual format::AnsiOutput* NewTempBuffer();
  virtual void PushColor(hnode_asdl::color_t e_color);
  virtual void PopColor();
  
  static constexpr uint32_t field_mask() {
    return ::format::ColorOutput::field_mask();
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(AnsiOutput));
  }

  DISALLOW_COPY_AND_ASSIGN(AnsiOutput)
};

extern int INDENT;
class _PrettyPrinter {
 public:
  _PrettyPrinter(int max_col);
  bool _PrintWrappedArray(List<hnode_asdl::hnode_t*>* array, int prefix_len, format::ColorOutput* f, int indent);
  bool _PrintWholeArray(List<hnode_asdl::hnode_t*>* array, int prefix_len, format::ColorOutput* f, int indent);
  void _PrintRecord(hnode::Record* node, format::ColorOutput* f, int indent);
  void PrintNode(hnode_asdl::hnode_t* node, format::ColorOutput* f, int indent);
  int max_col{};

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassScanned(0, sizeof(_PrettyPrinter));
  }

  DISALLOW_COPY_AND_ASSIGN(_PrettyPrinter)
};

bool _TrySingleLineObj(hnode::Record* node, format::ColorOutput* f, int max_chars);
bool _TrySingleLine(hnode_asdl::hnode_t* node, format::ColorOutput* f, int max_chars);
void PrintTree(hnode_asdl::hnode_t* node, format::ColorOutput* f);
void PrintTree2(hnode_asdl::hnode_t* node, format::ColorOutput* f);

}  // declare namespace format

namespace args {  // declare

using syntax_asdl::loc;
extern int String;
extern int Int;
extern int Float;
extern int Bool;
class _Attributes {
 public:
  _Attributes(Dict<BigStr*, value_asdl::value_t*>* defaults);
  void SetTrue(BigStr* name);
  void Set(BigStr* name, value_asdl::value_t* val);
  Dict<BigStr*, value_asdl::value_t*>* attrs{};
  List<Tuple2<BigStr*, bool>*>* opt_changes{};
  List<Tuple2<BigStr*, bool>*>* shopt_changes{};
  List<BigStr*>* actions{};
  bool show_options{};
  bool saw_double_dash{};

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassScanned(4, sizeof(_Attributes));
  }

  DISALLOW_COPY_AND_ASSIGN(_Attributes)
};

class Reader {
 public:
  Reader(List<BigStr*>* argv, List<syntax_asdl::CompoundWord*>* locs = nullptr);
  void Next();
  BigStr* Peek();
  Tuple2<BigStr*, syntax_asdl::loc_t*> Peek2();
  BigStr* ReadRequired(BigStr* error_msg);
  Tuple2<BigStr*, syntax_asdl::loc_t*> ReadRequired2(BigStr* error_msg);
  List<BigStr*>* Rest();
  Tuple2<List<BigStr*>*, List<syntax_asdl::CompoundWord*>*> Rest2();
  bool AtEnd();
  void Done();
  syntax_asdl::loc_t* _FirstLocation();
  syntax_asdl::loc_t* Location();
  List<BigStr*>* argv{};
  List<syntax_asdl::CompoundWord*>* locs{};
  int n{};
  int i{};

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassScanned(2, sizeof(Reader));
  }

  DISALLOW_COPY_AND_ASSIGN(Reader)
};

class _Action {
 public:
  _Action();
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);
  
  static constexpr uint32_t field_mask() {
    return kZeroMask;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(_Action));
  }

  DISALLOW_COPY_AND_ASSIGN(_Action)
};

class _ArgAction : public ::args::_Action {
 public:
  _ArgAction(BigStr* name, bool quit_parsing_flags, List<BigStr*>* valid = nullptr);
  virtual value_asdl::value_t* _Value(BigStr* arg, syntax_asdl::loc_t* location);
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);

  BigStr* name{};
  bool quit_parsing_flags{};
  List<BigStr*>* valid{};
  
  static constexpr uint32_t field_mask() {
    return ::args::_Action::field_mask()
         | maskbit(offsetof(_ArgAction, name))
         | maskbit(offsetof(_ArgAction, valid));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(_ArgAction));
  }

  DISALLOW_COPY_AND_ASSIGN(_ArgAction)
};

class SetToInt : public ::args::_ArgAction {
 public:
  SetToInt(BigStr* name);
  virtual value_asdl::value_t* _Value(BigStr* arg, syntax_asdl::loc_t* location);
  
  static constexpr uint32_t field_mask() {
    return ::args::_ArgAction::field_mask();
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetToInt));
  }

  DISALLOW_COPY_AND_ASSIGN(SetToInt)
};

class SetToFloat : public ::args::_ArgAction {
 public:
  SetToFloat(BigStr* name);
  virtual value_asdl::value_t* _Value(BigStr* arg, syntax_asdl::loc_t* location);
  
  static constexpr uint32_t field_mask() {
    return ::args::_ArgAction::field_mask();
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetToFloat));
  }

  DISALLOW_COPY_AND_ASSIGN(SetToFloat)
};

class SetToString : public ::args::_ArgAction {
 public:
  SetToString(BigStr* name, bool quit_parsing_flags, List<BigStr*>* valid = nullptr);
  virtual value_asdl::value_t* _Value(BigStr* arg, syntax_asdl::loc_t* location);
  
  static constexpr uint32_t field_mask() {
    return ::args::_ArgAction::field_mask();
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetToString));
  }

  DISALLOW_COPY_AND_ASSIGN(SetToString)
};

class SetAttachedBool : public ::args::_Action {
 public:
  SetAttachedBool(BigStr* name);
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);

  BigStr* name{};
  
  static constexpr uint32_t field_mask() {
    return ::args::_Action::field_mask()
         | maskbit(offsetof(SetAttachedBool, name));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetAttachedBool));
  }

  DISALLOW_COPY_AND_ASSIGN(SetAttachedBool)
};

class SetToTrue : public ::args::_Action {
 public:
  SetToTrue(BigStr* name);
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);

  BigStr* name{};
  
  static constexpr uint32_t field_mask() {
    return ::args::_Action::field_mask()
         | maskbit(offsetof(SetToTrue, name));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetToTrue));
  }

  DISALLOW_COPY_AND_ASSIGN(SetToTrue)
};

class SetOption : public ::args::_Action {
 public:
  SetOption(BigStr* name);
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);

  BigStr* name{};
  
  static constexpr uint32_t field_mask() {
    return ::args::_Action::field_mask()
         | maskbit(offsetof(SetOption, name));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetOption));
  }

  DISALLOW_COPY_AND_ASSIGN(SetOption)
};

class SetNamedOption : public ::args::_Action {
 public:
  SetNamedOption(bool shopt = false);
  void ArgName(BigStr* name);
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);

  List<BigStr*>* names{};
  bool shopt{};
  
  static constexpr uint32_t field_mask() {
    return ::args::_Action::field_mask()
         | maskbit(offsetof(SetNamedOption, names));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetNamedOption));
  }

  DISALLOW_COPY_AND_ASSIGN(SetNamedOption)
};

class SetAction : public ::args::_Action {
 public:
  SetAction(BigStr* name);
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);

  BigStr* name{};
  
  static constexpr uint32_t field_mask() {
    return ::args::_Action::field_mask()
         | maskbit(offsetof(SetAction, name));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetAction));
  }

  DISALLOW_COPY_AND_ASSIGN(SetAction)
};

class SetNamedAction : public ::args::_Action {
 public:
  SetNamedAction();
  void ArgName(BigStr* name);
  virtual bool OnMatch(BigStr* attached_arg, args::Reader* arg_r, args::_Attributes* out);

  List<BigStr*>* names{};
  
  static constexpr uint32_t field_mask() {
    return ::args::_Action::field_mask()
         | maskbit(offsetof(SetNamedAction, names));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SetNamedAction));
  }

  DISALLOW_COPY_AND_ASSIGN(SetNamedAction)
};

args::_Attributes* Parse(flag_spec::_FlagSpec* spec, args::Reader* arg_r);
args::_Attributes* ParseLikeEcho(flag_spec::_FlagSpec* spec, args::Reader* arg_r);
args::_Attributes* ParseMore(flag_spec::_FlagSpecAndMore* spec, args::Reader* arg_r);

}  // declare namespace args

#endif  // FRONTEND_ARGS_MYCPP_H
