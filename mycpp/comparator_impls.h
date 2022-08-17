#ifndef COMPARATOR_IMPLS_H
#define COMPARATOR_IMPLS_H

// NOTE(Jesse): There's different string compare logic in _multiple!_ places.
// @duplicated_to_oldstl_str_equals
// @duplicate_string_compare_code
//
bool str_equals(Str *left, Str *right) {
  // Fast path for identical strings.  String deduplication during GC could
  // make this more likely.  String interning could guarantee it, allowing us
  // to remove memcmp().
  if (left == right) {
    return true;
  }

  // obj_len_ equal implies string lengths are equal

  if (left->obj_len_ == right->obj_len_) {
    assert(len(left) == len(right));
    return memcmp(left->data_, right->data_, len(left)) == 0;
  }

  return false;
}

bool maybe_str_equals(Str* left, Str* right) {
  if (left && right) {
    return str_equals(left, right);
  }

  if (!left && !right) {
    return true;  // None == None
  }

  return false;  // one is None and one is a Str*
}

bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2) {
  bool result = are_equal(t1->at0(), t2->at0());
  result = result && (t1->at1() == t2->at1());
  return result;
}

// TODO(Jesse): Make an inline version of this
bool are_equal(Str *left, Str *right)
{
  return str_equals(left, right);
}

// TODO(Jesse): Make an inline version of this
bool are_equal(int left, int right)
{
  return left == right;
}

// TODO(Jesse): Make an inline version of this
bool keys_equal(int left, int right)
{
  return left == right;
}

// TODO(Jesse): Make an inline version of this
bool keys_equal(Str *left, Str *right)
{
  return are_equal(left, right);
}

#endif
