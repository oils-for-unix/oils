#ifndef MYCPP_COMPARATORS_H
#define MYCPP_COMPARATORS_H

class Str;

template <typename L, typename R>
class Tuple2;

bool str_equals(Str* left, Str* right);
bool maybe_str_equals(Str* left, Str* right);

bool are_equal(Str* left, Str* right);

bool are_equal(Str* left, Str* right);
bool are_equal(int left, int right);
bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2);

bool keys_equal(int left, int right);
bool keys_equal(Str* left, Str* right);

namespace id_kind_asdl {
enum class Kind;
};

bool are_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right);

#endif  // MYCPP_COMPARATORS_H
