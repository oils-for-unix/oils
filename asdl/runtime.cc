// BEGIN mycpp output

#include "runtime.h"

Str* str0 = new Str("(");
Str* str1 = new Str(")");
Str* str2 = new Str("_");
Str* str3 = new Str("T");
Str* str4 = new Str("F");
Str* str5 = new Str("\n<html>\n  <head>\n     <title>oil AST</title>\n     <style>\n      .n { color: brown }\n      .s { font-weight: bold }\n      .o { color: darkgreen }\n     </style>\n  </head>\n  <body>\n    <pre>\n");
Str* str6 = new Str("\n    </pre>\n  </body>\n</html>\n    ");
Str* str7 = new Str("n");
Str* str8 = new Str("s");
Str* str9 = new Str("o");
Str* str10 = new Str("o");
Str* str11 = new Str("o");
Str* str12 = new Str("<span class=\"%s\">");
Str* str13 = new Str("</span>");
Str* str14 = new Str(" ");
Str* str15 = new Str("\n");
Str* str16 = new Str(" ");
Str* str17 = new Str("]");
Str* str18 = new Str(" ");
Str* str19 = new Str(" ");
Str* str20 = new Str("\n");
Str* str21 = new Str("\n");
Str* str22 = new Str(" ");
Str* str23 = new Str("%s%s: [");
Str* str24 = new Str("\n");
Str* str25 = new Str("\n");
Str* str26 = new Str("%s]");
Str* str27 = new Str("%s%s: ");
Str* str28 = new Str("\n");
Str* str29 = new Str("\n");
Str* str30 = new Str(" ");
Str* str31 = new Str(" ");
Str* str32 = new Str(" ");
Str* str33 = new Str(" %s:");
Str* str34 = new Str("[");
Str* str35 = new Str(" ");
Str* str36 = new Str("]");
Str* str37 = new Str("\u001b[0;0m");
Str* str38 = new Str("\u001b[1m");
Str* str39 = new Str("\u001b[4m");
Str* str40 = new Str("\u001b[7m");
Str* str41 = new Str("\u001b[31m");
Str* str42 = new Str("\u001b[32m");
Str* str43 = new Str("\u001b[33m");
Str* str44 = new Str("\u001b[34m");
Str* str45 = new Str("&");
Str* str46 = new Str("&amp;");
Str* str47 = new Str("<");
Str* str48 = new Str("&lt;");
Str* str49 = new Str(">");
Str* str50 = new Str("&gt;");
Str* str51 = new Str("\\'\r\n\t\u0000");
Str* str52 = new Str("$'");
Str* str53 = new Str("'");
Str* str54 = new Str("'");
Str* str55 = new Str("");
Str* str56 = new Str("'");
Str* str57 = new Str("'");
Str* str58 = new Str("");
Str* str59 = new Str("'");
Str* str60 = new Str("'");
Str* str61 = new Str("");
Str* str62 = new Str("\\");
Str* str63 = new Str("\\\\");
Str* str64 = new Str("'");
Str* str65 = new Str("\\'");
Str* str66 = new Str("\n");
Str* str67 = new Str("\\n");
Str* str68 = new Str("\r");
Str* str69 = new Str("\\r");
Str* str70 = new Str("\t");
Str* str71 = new Str("\\t");
Str* str72 = new Str("\u0000");
Str* str73 = new Str("\\x00");
Str* str74 = new Str("\\0");
Str* str75 = new Str("");
Str* str76 = new Str("");
Str* str77 = new Str("");
Str* str78 = new Str("\\");
Str* str79 = new Str("\\\\");
Str* str80 = new Str("'");
Str* str81 = new Str("\\'");
Str* str82 = new Str("\n");
Str* str83 = new Str("\\n");
Str* str84 = new Str("\r");
Str* str85 = new Str("\\r");
Str* str86 = new Str("\t");
Str* str87 = new Str("\\t");
Str* str88 = new Str("\u0000");
Str* str89 = new Str("\\x00");
Str* str90 = new Str("\\0");

namespace ansi {  // forward declare

}  // forward declare namespace ansi

namespace cgi {  // forward declare

}  // forward declare namespace cgi

namespace qsn {  // forward declare

}  // forward declare namespace qsn

namespace ansi {  // declare
extern Str* RESET;
extern Str* BOLD;
extern Str* UNDERLINE;
extern Str* REVERSE;
extern Str* RED;
extern Str* GREEN;
extern Str* YELLOW;
extern Str* BLUE;

}  // declare namespace ansi

namespace cgi {  // declare
Str* escape(Str* s);

}  // declare namespace cgi

namespace qsn {  // declare
extern int BIT8_UTF8;
extern int BIT8_U_ESCAPE;
extern int BIT8_X_ESCAPE;
extern int MUST_QUOTE;
bool _encode(Str* s, int bit8_display, bool shell_compat, List<Str*>* parts);
Str* maybe_shell_encode(Str* s);
Str* maybe_shell_encode(Str* s, int flags);
Str* maybe_encode(Str* s);
Str* maybe_encode(Str* s, int bit8_display);
Str* encode(Str* s, int bit8_display);
void _encode_bytes_x(Str* s, bool shell_compat, List<Str*>* parts);
extern int Ascii;
extern int Begin2;
extern int Begin3;
extern int Begin4;
extern int Cont;
extern int Invalid;
extern int Start;
extern int B2_1;
extern int B3_1;
extern int B4_1;
extern int B3_2;
extern int B4_2;
extern int B4_3;
bool _encode_runes(Str* s, int bit8_display, bool shell_compat, List<Str*>* parts);
Str* maybe_tsv_encode(Str* s, int bit8_display);
Str* tsv_decode(Str* s);

}  // declare namespace qsn

namespace runtime {  // define
using hnode_asdl::hnode__Record;
using hnode_asdl::hnode__Leaf;
using hnode_asdl::color_t;
using hnode_asdl::color_e;
int NO_SPID = -1;

hnode_asdl::hnode__Record* NewRecord(Str* node_type) {
  return new hnode__Record(node_type, new List<hnode_asdl::field*>(), false, str0, str1, new List<hnode_asdl::hnode_t*>());
}

hnode_asdl::hnode__Leaf* NewLeaf(Str* s, hnode_asdl::color_t e_color) {
  if (s == nullptr) {
    return new hnode__Leaf(str2, color_e::OtherConst);
  }
  else {
    return new hnode__Leaf(s, e_color);
  }
}
Str* TRUE_STR = str3;
Str* FALSE_STR = str4;

}  // define namespace runtime

namespace format {  // define
namespace hnode_e = hnode_asdl::hnode_e;
using hnode_asdl::hnode_t;
using hnode_asdl::hnode__Record;
using hnode_asdl::hnode__Array;
using hnode_asdl::hnode__Leaf;
using hnode_asdl::hnode__External;
using hnode_asdl::color_e;
using hnode_asdl::color_t;
using hnode_asdl::color_str;
using hnode_asdl::hnode_str;

format::ColorOutput* DetectConsoleOutput(mylib::Writer* f) {
  if (f->isatty()) {
    return new AnsiOutput(f);
  }
  else {
    return new TextOutput(f);
  }
}

ColorOutput::ColorOutput(mylib::Writer* f) {
  this->f = f;
  this->num_chars = 0;
}

format::ColorOutput* ColorOutput::NewTempBuffer() {
  throw new NotImplementedError();
}

void ColorOutput::FileHeader() {
  ;  // pass
}

void ColorOutput::FileFooter() {
  ;  // pass
}

void ColorOutput::PushColor(hnode_asdl::color_t e_color) {
  throw new NotImplementedError();
}

void ColorOutput::PopColor() {
  throw new NotImplementedError();
}

void ColorOutput::write(Str* s) {
  this->f->write(s);
  this->num_chars += len(s);
}

void ColorOutput::WriteRaw(Tuple2<Str*, int>* raw) {
  Str* s;
  int num_chars;

  Tuple2<Str*, int>* tup0 = raw;
  s = tup0->at0();
  num_chars = tup0->at1();
  this->f->write(s);
  this->num_chars += num_chars;
}

int ColorOutput::NumChars() {
  return this->num_chars;
}

Tuple2<Str*, int> ColorOutput::GetRaw() {
  mylib::BufWriter* f = static_cast<mylib::BufWriter*>(this->f);
  return (Tuple2<Str*, int>(f->getvalue(), this->num_chars));
}

TextOutput::TextOutput(mylib::Writer* f) : ColorOutput(f) {
}

format::TextOutput* TextOutput::NewTempBuffer() {
  return new TextOutput(new mylib::BufWriter());
}

void TextOutput::PushColor(hnode_asdl::color_t e_color) {
  ;  // pass
}

void TextOutput::PopColor() {
  ;  // pass
}

HtmlOutput::HtmlOutput(mylib::Writer* f) : ColorOutput(f) {
}

format::HtmlOutput* HtmlOutput::NewTempBuffer() {
  return new HtmlOutput(new mylib::BufWriter());
}

void HtmlOutput::FileHeader() {
  this->f->write(str5);
}

void HtmlOutput::FileFooter() {
  this->f->write(str6);
}

void HtmlOutput::PushColor(hnode_asdl::color_t e_color) {
  Str* css_class;

  if (e_color == color_e::TypeName) {
    css_class = str7;
  }
  else {
    if (e_color == color_e::StringConst) {
      css_class = str8;
    }
    else {
      if (e_color == color_e::OtherConst) {
        css_class = str9;
      }
      else {
        if (e_color == color_e::External) {
          css_class = str10;
        }
        else {
          if (e_color == color_e::UserType) {
            css_class = str11;
          }
          else {
            throw new AssertionError();
          }
        }
      }
    }
  }
  this->f->write(fmt0(css_class));
}

void HtmlOutput::PopColor() {
  this->f->write(str13);
}

void HtmlOutput::write(Str* s) {
  this->f->write(cgi::escape(s));
  this->num_chars += len(s);
}

AnsiOutput::AnsiOutput(mylib::Writer* f) : ColorOutput(f) {
}

format::AnsiOutput* AnsiOutput::NewTempBuffer() {
  return new AnsiOutput(new mylib::BufWriter());
}

void AnsiOutput::PushColor(hnode_asdl::color_t e_color) {
  if (e_color == color_e::TypeName) {
    this->f->write(ansi::YELLOW);
  }
  else {
    if (e_color == color_e::StringConst) {
      this->f->write(ansi::BOLD);
    }
    else {
      if (e_color == color_e::OtherConst) {
        this->f->write(ansi::GREEN);
      }
      else {
        if (e_color == color_e::External) {
          this->f->write(str_concat(ansi::BOLD, ansi::BLUE));
        }
        else {
          if (e_color == color_e::UserType) {
            this->f->write(ansi::GREEN);
          }
          else {
            throw new AssertionError();
          }
        }
      }
    }
  }
}

void AnsiOutput::PopColor() {
  this->f->write(ansi::RESET);
}
int INDENT = 2;

_PrettyPrinter::_PrettyPrinter(int max_col) {
  this->max_col = max_col;
}

bool _PrettyPrinter::_PrintWrappedArray(List<hnode_asdl::hnode_t*>* array, int prefix_len, format::ColorOutput* f, int indent) {
  bool all_fit;
  int chars_so_far;
  int i;
  format::ColorOutput* single_f;
  Str* s;
  int num_chars;

  all_fit = true;
  chars_so_far = prefix_len;
  i = 0;
  for (ListIter<hnode_asdl::hnode_t*> it(array); !it.Done(); it.Next(), ++i) {
    hnode_asdl::hnode_t* val = it.Value();
    if (i != 0) {
      f->write(str14);
    }
    single_f = f->NewTempBuffer();
    if (_TrySingleLine(val, single_f, this->max_col - chars_so_far)) {
      Tuple2<Str*, int> tup1 = single_f->GetRaw();
      s = tup1.at0();
      num_chars = tup1.at1();
      f->WriteRaw((new Tuple2<Str*, int>(s, num_chars)));
      chars_so_far += single_f->NumChars();
    }
    else {
      f->write(str15);
      this->PrintNode(val, f, indent + INDENT);
      chars_so_far = 0;
      all_fit = false;
    }
  }
  return all_fit;
}

bool _PrettyPrinter::_PrintWholeArray(List<hnode_asdl::hnode_t*>* array, int prefix_len, format::ColorOutput* f, int indent) {
  bool all_fit;
  List<Tuple2<Str*, int>*>* pieces;
  int chars_so_far;
  format::ColorOutput* single_f;
  Str* s;
  int num_chars;
  int i;

  all_fit = true;
  pieces = new List<Tuple2<Str*, int>*>();
  chars_so_far = prefix_len;
  for (ListIter<hnode_asdl::hnode_t*> it(array); !it.Done(); it.Next()) {
    hnode_asdl::hnode_t* item = it.Value();
    single_f = f->NewTempBuffer();
    if (_TrySingleLine(item, single_f, this->max_col - chars_so_far)) {
      Tuple2<Str*, int> tup2 = single_f->GetRaw();
      s = tup2.at0();
      num_chars = tup2.at1();
      pieces->append((new Tuple2<Str*, int>(s, num_chars)));
      chars_so_far += single_f->NumChars();
    }
    else {
      all_fit = false;
      break;
    }
  }
  if (all_fit) {
    i = 0;
    for (ListIter<Tuple2<Str*, int>*> it(pieces); !it.Done(); it.Next(), ++i) {
      Tuple2<Str*, int>* p = it.Value();
      if (i != 0) {
        f->write(str16);
      }
      f->WriteRaw(p);
    }
    f->write(str17);
  }
  return all_fit;
}

void _PrettyPrinter::_PrintRecord(hnode_asdl::hnode__Record* node, format::ColorOutput* f, int indent) {
  Str* ind;
  Str* prefix;
  int prefix_len;
  bool all_fit;
  int i;
  Str* name;
  hnode_asdl::hnode_t* val;
  Str* ind1;
  hnode_asdl::hnode_t* UP_val;
  int tag;
  Str* name_str;
  format::ColorOutput* single_f;
  Str* s;
  int num_chars;

  ind = str_repeat(str18, indent);
  if (node->abbrev) {
    prefix = str_concat(ind, node->left);
    f->write(prefix);
    if (len(node->node_type)) {
      f->PushColor(color_e::TypeName);
      f->write(node->node_type);
      f->PopColor();
      f->write(str19);
    }
    prefix_len = len(prefix) + len(node->node_type) + 1;
    all_fit = this->_PrintWrappedArray(node->unnamed_fields, prefix_len, f, indent);
    if (!all_fit) {
      f->write(str20);
      f->write(ind);
    }
    f->write(node->right);
  }
  else {
    f->write(str_concat(ind, node->left));
    f->PushColor(color_e::TypeName);
    f->write(node->node_type);
    f->PopColor();
    f->write(str21);
    i = 0;
    for (ListIter<hnode_asdl::field*> it(node->fields); !it.Done(); it.Next()) {
      hnode_asdl::field* field = it.Value();
      name = field->name;
      val = field->val;
      ind1 = str_repeat(str22, indent + INDENT);
      UP_val = val;
      tag = val->tag_();
      if (tag == hnode_e::Array) {
        hnode__Array* val = static_cast<hnode__Array*>(UP_val);
        name_str = fmt1(ind1, name);
        f->write(name_str);
        prefix_len = len(name_str);
        if (!this->_PrintWholeArray(val->children, prefix_len, f, indent)) {
          f->write(str24);
          for (ListIter<hnode_asdl::hnode_t*> it(val->children); !it.Done(); it.Next()) {
            hnode_asdl::hnode_t* child = it.Value();
            this->PrintNode(child, f, indent + INDENT + INDENT);
            f->write(str25);
          }
          f->write(fmt2(ind1));
        }
      }
      else {
        name_str = fmt3(ind1, name);
        f->write(name_str);
        prefix_len = len(name_str);
        single_f = f->NewTempBuffer();
        if (_TrySingleLine(val, single_f, this->max_col - prefix_len)) {
          Tuple2<Str*, int> tup3 = single_f->GetRaw();
          s = tup3.at0();
          num_chars = tup3.at1();
          f->WriteRaw((new Tuple2<Str*, int>(s, num_chars)));
        }
        else {
          f->write(str28);
          this->PrintNode(val, f, indent + INDENT + INDENT);
        }
        i += 1;
      }
      f->write(str29);
    }
    f->write(str_concat(ind, node->right));
  }
}

void _PrettyPrinter::PrintNode(hnode_asdl::hnode_t* node, format::ColorOutput* f, int indent) {
  Str* ind;
  format::ColorOutput* single_f;
  Str* s;
  int num_chars;
  hnode_asdl::hnode_t* UP_node;
  int tag;

  ind = str_repeat(str30, indent);
  single_f = f->NewTempBuffer();
  single_f->write(ind);
  if (_TrySingleLine(node, single_f, this->max_col - indent)) {
    Tuple2<Str*, int> tup4 = single_f->GetRaw();
    s = tup4.at0();
    num_chars = tup4.at1();
    f->WriteRaw((new Tuple2<Str*, int>(s, num_chars)));
    return ;
  }
  UP_node = node;
  tag = node->tag_();
  if (tag == hnode_e::Leaf) {
    hnode__Leaf* node = static_cast<hnode__Leaf*>(UP_node);
    f->PushColor(node->color);
    f->write(qsn::maybe_encode(node->s));
    f->PopColor();
  }
  else {
    if (tag == hnode_e::External) {
      hnode__External* node = static_cast<hnode__External*>(UP_node);
      f->PushColor(color_e::External);
      f->write(repr(node->obj));
      f->PopColor();
    }
    else {
      if (tag == hnode_e::Record) {
        hnode__Record* node = static_cast<hnode__Record*>(UP_node);
        this->_PrintRecord(node, f, indent);
      }
      else {
        throw new AssertionError();
      }
    }
  }
}

bool _TrySingleLineObj(hnode_asdl::hnode__Record* node, format::ColorOutput* f, int max_chars) {
  int i;

  f->write(node->left);
  if (node->abbrev) {
    if (len(node->node_type)) {
      f->PushColor(color_e::TypeName);
      f->write(node->node_type);
      f->PopColor();
      f->write(str31);
    }
    i = 0;
    for (ListIter<hnode_asdl::hnode_t*> it(node->unnamed_fields); !it.Done(); it.Next(), ++i) {
      hnode_asdl::hnode_t* val = it.Value();
      if (i != 0) {
        f->write(str32);
      }
      if (!_TrySingleLine(val, f, max_chars)) {
        return false;
      }
    }
  }
  else {
    f->PushColor(color_e::TypeName);
    f->write(node->node_type);
    f->PopColor();
    for (ListIter<hnode_asdl::field*> it(node->fields); !it.Done(); it.Next()) {
      hnode_asdl::field* field = it.Value();
      f->write(fmt4(field->name));
      if (!_TrySingleLine(field->val, f, max_chars)) {
        return false;
      }
    }
  }
  f->write(node->right);
  return true;
}

bool _TrySingleLine(hnode_asdl::hnode_t* node, format::ColorOutput* f, int max_chars) {
  hnode_asdl::hnode_t* UP_node;
  int tag;
  int i;
  int num_chars_so_far;

  UP_node = node;
  tag = node->tag_();
  if (tag == hnode_e::Leaf) {
    hnode__Leaf* node = static_cast<hnode__Leaf*>(UP_node);
    f->PushColor(node->color);
    f->write(qsn::maybe_encode(node->s));
    f->PopColor();
  }
  else {
    if (tag == hnode_e::External) {
      hnode__External* node = static_cast<hnode__External*>(UP_node);
      f->PushColor(color_e::External);
      f->write(repr(node->obj));
      f->PopColor();
    }
    else {
      if (tag == hnode_e::Array) {
        hnode__Array* node = static_cast<hnode__Array*>(UP_node);
        f->write(str34);
        i = 0;
        for (ListIter<hnode_asdl::hnode_t*> it(node->children); !it.Done(); it.Next(), ++i) {
          hnode_asdl::hnode_t* item = it.Value();
          if (i != 0) {
            f->write(str35);
          }
          if (!_TrySingleLine(item, f, max_chars)) {
            return false;
          }
        }
        f->write(str36);
      }
      else {
        if (tag == hnode_e::Record) {
          hnode__Record* node = static_cast<hnode__Record*>(UP_node);
          return _TrySingleLineObj(node, f, max_chars);
        }
        else {
          throw new AssertionError();
        }
      }
    }
  }
  num_chars_so_far = f->NumChars();
  if (num_chars_so_far > max_chars) {
    return false;
  }
  return true;
}

void PrintTree(hnode_asdl::hnode_t* node, format::ColorOutput* f) {
  format::_PrettyPrinter* pp;

  pp = new _PrettyPrinter(100);
  pp->PrintNode(node, f, 0);
}

}  // define namespace format

namespace ansi {  // define
Str* RESET = str37;
Str* BOLD = str38;
Str* UNDERLINE = str39;
Str* REVERSE = str40;
Str* RED = str41;
Str* GREEN = str42;
Str* YELLOW = str43;
Str* BLUE = str44;

}  // define namespace ansi

namespace cgi {  // define

Str* escape(Str* s) {
  s = s->replace(str45, str46);
  s = s->replace(str47, str48);
  s = s->replace(str49, str50);
  return s;
}

}  // define namespace cgi

namespace qsn {  // define
int BIT8_UTF8 = 0;
int BIT8_U_ESCAPE = 1;
int BIT8_X_ESCAPE = 2;
int MUST_QUOTE = 4;

bool _encode(Str* s, int bit8_display, bool shell_compat, List<Str*>* parts) {
  if (bit8_display == BIT8_X_ESCAPE) {
    _encode_bytes_x(s, shell_compat, parts);
    return true;
  }
  else {
    return _encode_runes(s, bit8_display, shell_compat, parts);
  }
}

Str* maybe_shell_encode(Str* s) {
  return maybe_shell_encode(s, 0);
}

Str* maybe_shell_encode(Str* s, int flags) {
  int quote;
  int must_quote;
  int bit8_display;
  List<Str*>* parts;
  bool valid_utf8;
  Str* prefix;

  quote = 0;
  must_quote = flags & 4;
  bit8_display = flags & 3;
  if (len(s) == 0) {
    quote = 1;
  }
  else {
    for (StrIter it(s); !it.Done(); it.Next()) {
      Str* ch = it.Value();
      if (!must_quote and IsPlainChar(ch)) {
        continue;
      }
      quote = 1;
      if (str_contains(str51, ch) or IsUnprintableLow(ch)) {
        quote = 2;
        break;
      }
    }
  }
  if (quote == 0) {
    return s;
  }
  parts = new List<Str*>();
  valid_utf8 = _encode(s, bit8_display, true, parts);
  if (!valid_utf8 or quote == 2) {
    prefix = str52;
  }
  else {
    prefix = str53;
  }
  parts->append(str54);
  return str_concat(prefix, str55->join(parts));
}

Str* maybe_encode(Str* s) {
  return maybe_encode(s, BIT8_UTF8);
}

Str* maybe_encode(Str* s, int bit8_display) {
  int quote;
  List<Str*>* parts;

  quote = 0;
  if (len(s) == 0) {
    quote = 1;
  }
  else {
    for (StrIter it(s); !it.Done(); it.Next()) {
      Str* ch = it.Value();
      if (IsPlainChar(ch)) {
        continue;
      }
      quote = 1;
    }
  }
  if (!quote) {
    return s;
  }
  parts = new List<Str*>();
  parts->append(str56);
  _encode(s, bit8_display, false, parts);
  parts->append(str57);
  return str58->join(parts);
}

Str* encode(Str* s, int bit8_display) {
  List<Str*>* parts;

  parts = new List<Str*>();
  parts->append(str59);
  _encode(s, bit8_display, false, parts);
  parts->append(str60);
  return str61->join(parts);
}

void _encode_bytes_x(Str* s, bool shell_compat, List<Str*>* parts) {
  Str* part;

  for (StrIter it(s); !it.Done(); it.Next()) {
    Str* byte = it.Value();
    if (str_equals(byte, str62)) {
      part = str63;
    }
    else {
      if (str_equals(byte, str64)) {
        part = str65;
      }
      else {
        if (str_equals(byte, str66)) {
          part = str67;
        }
        else {
          if (str_equals(byte, str68)) {
            part = str69;
          }
          else {
            if (str_equals(byte, str70)) {
              part = str71;
            }
            else {
              if (str_equals(byte, str72)) {
                part = shell_compat ? str73 : str74;
              }
              else {
                if (IsUnprintableLow(byte)) {
                  part = XEscape(byte);
                }
                else {
                  if (IsUnprintableHigh(byte)) {
                    part = XEscape(byte);
                  }
                  else {
                    part = byte;
                  }
                }
              }
            }
          }
        }
      }
    }
    parts->append(part);
  }
}
int Ascii = 0;
int Begin2 = 1;
int Begin3 = 2;
int Begin4 = 3;
int Cont = 4;
int Invalid = 5;
int Start = 0;
int B2_1 = 1;
int B3_1 = 2;
int B4_1 = 3;
int B3_2 = 4;
int B4_2 = 5;
int B4_3 = 6;

bool _encode_runes(Str* s, int bit8_display, bool shell_compat, List<Str*>* parts) {
  bool valid_utf8;
  int state;
  Str* r1;
  Str* r2;
  Str* r3;
  int b;
  int typ;
  Str* out;
  int rune;

  valid_utf8 = true;
  state = Start;
  r1 = str75;
  r2 = str76;
  r3 = str77;
  for (StrIter it(s); !it.Done(); it.Next()) {
    Str* byte = it.Value();
    b = ord(byte);
    if (b < 127) {
      typ = Ascii;
    }
    else {
      if (b >> 6 == 2) {
        typ = Cont;
      }
      else {
        if (b >> 5 == 6) {
          typ = Begin2;
        }
        else {
          if (b >> 4 == 14) {
            typ = Begin3;
          }
          else {
            if (b >> 3 == 30) {
              typ = Begin4;
            }
            else {
              typ = Invalid;
            }
          }
        }
      }
    }
    if (typ != Cont) {
      if (state >= B2_1) {
        valid_utf8 = false;
        parts->append(XEscape(r1));
      }
      if (state >= B3_2) {
        parts->append(XEscape(r2));
      }
      if (state >= B4_3) {
        parts->append(XEscape(r3));
      }
    }
    if (typ == Ascii) {
      state = Start;
      if (str_equals(byte, str78)) {
        out = str79;
      }
      else {
        if (str_equals(byte, str80)) {
          out = str81;
        }
        else {
          if (str_equals(byte, str82)) {
            out = str83;
          }
          else {
            if (str_equals(byte, str84)) {
              out = str85;
            }
            else {
              if (str_equals(byte, str86)) {
                out = str87;
              }
              else {
                if (str_equals(byte, str88)) {
                  out = shell_compat ? str89 : str90;
                }
                else {
                  if (IsUnprintableLow(byte)) {
                    if (bit8_display == BIT8_U_ESCAPE) {
                      out = UEscape(ord(byte));
                    }
                    else {
                      out = XEscape(byte);
                    }
                  }
                  else {
                    out = byte;
                  }
                }
              }
            }
          }
        }
      }
      parts->append(out);
    }
    else {
      if (typ == Begin2) {
        state = B2_1;
        r1 = byte;
      }
      else {
        if (typ == Begin3) {
          state = B3_1;
          r1 = byte;
        }
        else {
          if (typ == Begin4) {
            state = B4_1;
            r1 = byte;
          }
          else {
            if (typ == Invalid) {
              state = Start;
              parts->append(XEscape(byte));
              valid_utf8 = false;
            }
            else {
              if (typ == Cont) {
                if (state == Start) {
                  parts->append(XEscape(byte));
                  valid_utf8 = false;
                }
                else {
                  if (state == B2_1) {
                    if (bit8_display == BIT8_UTF8) {
                      out = str_concat(r1, byte);
                    }
                    else {
                      rune = ord(byte) & 63;
                      rune |= ord(r1) & 31 << 6;
                      out = UEscape(rune);
                    }
                    parts->append(out);
                    state = Start;
                  }
                  else {
                    if (state == B3_1) {
                      r2 = byte;
                      state = B3_2;
                    }
                    else {
                      if (state == B3_2) {
                        if (bit8_display == BIT8_UTF8) {
                          out = str_concat(str_concat(r1, r2), byte);
                        }
                        else {
                          rune = ord(byte) & 63;
                          rune |= ord(r2) & 63 << 6;
                          rune |= ord(r1) & 15 << 12;
                          out = UEscape(rune);
                        }
                        parts->append(out);
                        state = Start;
                      }
                      else {
                        if (state == B4_1) {
                          r2 = byte;
                          state = B4_2;
                        }
                        else {
                          if (state == B4_2) {
                            r3 = byte;
                            state = B4_3;
                          }
                          else {
                            if (state == B4_3) {
                              if (bit8_display == BIT8_UTF8) {
                                out = str_concat(str_concat(str_concat(r1, r2), r3), byte);
                              }
                              else {
                                rune = ord(byte) & 63;
                                rune |= ord(r3) & 63 << 6;
                                rune |= ord(r2) & 63 << 12;
                                rune |= ord(r1) & 7 << 18;
                                out = UEscape(rune);
                              }
                              parts->append(out);
                              state = Start;
                            }
                            else {
                              throw new AssertionError();
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
              else {
                throw new AssertionError();
              }
            }
          }
        }
      }
    }
  }
  if (state >= B2_1) {
    valid_utf8 = false;
    parts->append(XEscape(r1));
  }
  if (state >= B3_2) {
    parts->append(XEscape(r2));
  }
  if (state >= B4_3) {
    parts->append(XEscape(r3));
  }
  return valid_utf8;
}

Str* maybe_tsv_encode(Str* s, int bit8_display) {
  ;  // pass
}

Str* tsv_decode(Str* s) {
  ;  // pass
}

}  // define namespace qsn

