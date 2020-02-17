// postamble.cc
// This is INCLUDED at the end of the mycpp generated code.
// That code uses optview declarations, so it needs this definition.

namespace optview {

#ifndef OSH_PARSE  // hack for osh_parse, set in build/mycpp.sh
bool Exec::errexit() {
  return errexit_->value();
}
#endif  // OSH_PARSE

}  // namespace optview
