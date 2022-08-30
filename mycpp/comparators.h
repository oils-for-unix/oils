

class Str;

template <typename L, typename R>
class Tuple2;

bool str_equals(Str *left, Str *right);
bool maybe_str_equals(Str* left, Str* right);



bool are_equal(Str *left, Str *right);
bool are_equal(int left, int right);
bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2);

bool keys_equal(int left, int right);
bool keys_equal(Str *left, Str *right);
