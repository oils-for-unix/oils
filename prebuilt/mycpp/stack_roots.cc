#define SOUFFLE_GENERATOR_VERSION "2.4.1-26-gc7ce22981"
#include "souffle/CompiledSouffle.h"
#include "souffle/SignalHandler.h"
#include "souffle/SouffleInterface.h"
#include "souffle/datastructure/BTree.h"
#include "souffle/io/IOSystem.h"
#include "souffle/utility/MiscUtil.h"
#include <any>
namespace functors {
extern "C" {
}
} //namespace functors
namespace souffle::t_btree_000_iii__0_1_2__111 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 3;
using t_tuple = Tuple<RamDomain, 3>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iii__0_1_2__111 
namespace souffle::t_btree_000_iii__0_1_2__111 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[3];
std::copy(ramDomain, ramDomain + 3, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2) {
RamDomain data[3] = {a0,a1,a2};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_111(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 3 direct b-tree index 0 lex-order [0,1,2]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_iii__0_1_2__111 
namespace souffle::t_btree_000_iiii__0_1_2_3__1111 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 4;
using t_tuple = Tuple<RamDomain, 4>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3])) ? -1 : (ramBitCast<RamSigned>(a[3]) > ramBitCast<RamSigned>(b[3])) ? 1 :(0))));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3]))))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iiii__0_1_2_3__1111 
namespace souffle::t_btree_000_iiii__0_1_2_3__1111 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[4];
std::copy(ramDomain, ramDomain + 4, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3) {
RamDomain data[4] = {a0,a1,a2,a3};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1111(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 4 direct b-tree index 0 lex-order [0,1,2,3]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_iiii__0_1_2_3__1111 
namespace souffle::t_btree_000_ii__0_1__11 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 2;
using t_tuple = Tuple<RamDomain, 2>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :(0));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_ii__0_1__11 
namespace souffle::t_btree_000_ii__0_1__11 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[2];
std::copy(ramDomain, ramDomain + 2, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1) {
RamDomain data[2] = {a0,a1};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_11(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 2 direct b-tree index 0 lex-order [0,1]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_ii__0_1__11 
namespace souffle::t_btree_000_i__0__1 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 1;
using t_tuple = Tuple<RamDomain, 1>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :(0);
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_0(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_0(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_1(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_1(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_i__0__1 
namespace souffle::t_btree_000_i__0__1 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[1];
std::copy(ramDomain, ramDomain + 1, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0) {
RamDomain data[1] = {a0};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_0(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_0(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_1(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_1(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 1 direct b-tree index 0 lex-order [0]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_i__0__1 
namespace souffle::t_btree_000_ii__1_0__11__01 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 2;
using t_tuple = Tuple<RamDomain, 2>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :(0));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_0::iterator> lowerUpperRange_01(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_01(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_ii__1_0__11__01 
namespace souffle::t_btree_000_ii__1_0__11__01 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[2];
std::copy(ramDomain, ramDomain + 2, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1) {
RamDomain data[2] = {a0,a1};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_11(lower,upper,h);
}
range<t_ind_0::iterator> Type::lowerUpperRange_01(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_01(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_01(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 2 direct b-tree index 0 lex-order [1,0]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_ii__1_0__11__01 
namespace souffle::t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 4;
using t_tuple = Tuple<RamDomain, 4>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]));
 }
};
using t_ind_0 = btree_multiset<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
struct t_comparator_1{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3])) ? -1 : (ramBitCast<RamSigned>(a[3]) > ramBitCast<RamSigned>(b[3])) ? 1 :((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :(0))));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3]))|| ((ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3])) && ((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3]))&&(ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]));
 }
};
using t_ind_1 = btree_set<t_tuple,t_comparator_1>;
t_ind_1 ind_1;
using iterator = t_ind_1::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
t_ind_1::operation_hints hints_1_lower;
t_ind_1::operation_hints hints_1_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_1::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_1::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_1::iterator> lowerUpperRange_0001(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_1::iterator> lowerUpperRange_0001(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001 
namespace souffle::t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using t_ind_1 = Type::t_ind_1;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_1.insert(t, h.hints_1_lower)) {
ind_0.insert(t, h.hints_0_lower);
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[4];
std::copy(ramDomain, ramDomain + 4, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3) {
RamDomain data[4] = {a0,a1,a2,a3};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_1.contains(t, h.hints_1_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_1.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_1.find(t, h.hints_1_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_1.begin(),ind_1.end());
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_1.begin(),ind_1.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1110(lower,upper,h);
}
range<t_ind_1::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_1 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_1.find(lower, h.hints_1_lower);
    auto fin = ind_1.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_1.end(), ind_1.end());
}
return make_range(ind_1.lower_bound(lower, h.hints_1_lower), ind_1.upper_bound(upper, h.hints_1_upper));
}
range<t_ind_1::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1111(lower,upper,h);
}
range<t_ind_1::iterator> Type::lowerUpperRange_0001(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_1 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_1.end(), ind_1.end());
}
return make_range(ind_1.lower_bound(lower, h.hints_1_lower), ind_1.upper_bound(upper, h.hints_1_upper));
}
range<t_ind_1::iterator> Type::lowerUpperRange_0001(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_0001(lower,upper,h);
}
bool Type::empty() const {
return ind_1.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_1.getChunks(400);
}
void Type::purge() {
ind_0.clear();
ind_1.clear();
}
iterator Type::begin() const {
return ind_1.begin();
}
iterator Type::end() const {
return ind_1.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 4 direct b-tree index 0 lex-order [0,1,2]\n";
ind_0.printStats(o);
o << " arity 4 direct b-tree index 1 lex-order [3,0,1,2]\n";
ind_1.printStats(o);
}
} // namespace souffle::t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001 
namespace souffle::t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 4;
using t_tuple = Tuple<RamDomain, 4>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3])) ? -1 : (ramBitCast<RamSigned>(a[3]) > ramBitCast<RamSigned>(b[3])) ? 1 :((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3]))|| ((ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3])) && ((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3]))&&(ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]));
 }
};
using t_ind_0 = btree_multiset<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
struct t_comparator_1{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3])) ? -1 : (ramBitCast<RamSigned>(a[3]) > ramBitCast<RamSigned>(b[3])) ? 1 :(0))));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3]))))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3]));
 }
};
using t_ind_1 = btree_set<t_tuple,t_comparator_1>;
t_ind_1 ind_1;
using iterator = t_ind_1::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
t_ind_1::operation_hints hints_1_lower;
t_ind_1::operation_hints hints_1_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_1::iterator> lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_1::iterator> lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_1::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_1::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_0::iterator> lowerUpperRange_0011(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_0011(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011 
namespace souffle::t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using t_ind_1 = Type::t_ind_1;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_1.insert(t, h.hints_1_lower)) {
ind_0.insert(t, h.hints_0_lower);
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[4];
std::copy(ramDomain, ramDomain + 4, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3) {
RamDomain data[4] = {a0,a1,a2,a3};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_1.contains(t, h.hints_1_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_1.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_1.find(t, h.hints_1_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_1.begin(),ind_1.end());
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_1.begin(),ind_1.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1011(lower,upper,h);
}
range<t_ind_1::iterator> Type::lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_1 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_1.end(), ind_1.end());
}
return make_range(ind_1.lower_bound(lower, h.hints_1_lower), ind_1.upper_bound(upper, h.hints_1_upper));
}
range<t_ind_1::iterator> Type::lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1110(lower,upper,h);
}
range<t_ind_1::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_1 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_1.find(lower, h.hints_1_lower);
    auto fin = ind_1.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_1.end(), ind_1.end());
}
return make_range(ind_1.lower_bound(lower, h.hints_1_lower), ind_1.upper_bound(upper, h.hints_1_upper));
}
range<t_ind_1::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1111(lower,upper,h);
}
range<t_ind_0::iterator> Type::lowerUpperRange_0011(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_0011(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_0011(lower,upper,h);
}
bool Type::empty() const {
return ind_1.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_1.getChunks(400);
}
void Type::purge() {
ind_0.clear();
ind_1.clear();
}
iterator Type::begin() const {
return ind_1.begin();
}
iterator Type::end() const {
return ind_1.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 4 direct b-tree index 0 lex-order [2,3,0]\n";
ind_0.printStats(o);
o << " arity 4 direct b-tree index 1 lex-order [0,1,2,3]\n";
ind_1.printStats(o);
}
} // namespace souffle::t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011 
namespace souffle::t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 4;
using t_tuple = Tuple<RamDomain, 4>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3])) ? -1 : (ramBitCast<RamSigned>(a[3]) > ramBitCast<RamSigned>(b[3])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3]));
 }
};
using t_ind_0 = btree_multiset<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
struct t_comparator_1{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3])) ? -1 : (ramBitCast<RamSigned>(a[3]) > ramBitCast<RamSigned>(b[3])) ? 1 :(0))));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3]))))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3]));
 }
};
using t_ind_1 = btree_set<t_tuple,t_comparator_1>;
t_ind_1 ind_1;
using iterator = t_ind_1::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
t_ind_1::operation_hints hints_1_lower;
t_ind_1::operation_hints hints_1_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_1::iterator> lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_1::iterator> lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_1::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_1::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111 
namespace souffle::t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using t_ind_1 = Type::t_ind_1;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_1.insert(t, h.hints_1_lower)) {
ind_0.insert(t, h.hints_0_lower);
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[4];
std::copy(ramDomain, ramDomain + 4, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3) {
RamDomain data[4] = {a0,a1,a2,a3};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_1.contains(t, h.hints_1_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_1.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_1.find(t, h.hints_1_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_1.begin(),ind_1.end());
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_1.begin(),ind_1.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_1011(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1011(lower,upper,h);
}
range<t_ind_1::iterator> Type::lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_1 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_1.end(), ind_1.end());
}
return make_range(ind_1.lower_bound(lower, h.hints_1_lower), ind_1.upper_bound(upper, h.hints_1_upper));
}
range<t_ind_1::iterator> Type::lowerUpperRange_1110(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1110(lower,upper,h);
}
range<t_ind_1::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_1 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_1.find(lower, h.hints_1_lower);
    auto fin = ind_1.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_1.end(), ind_1.end());
}
return make_range(ind_1.lower_bound(lower, h.hints_1_lower), ind_1.upper_bound(upper, h.hints_1_upper));
}
range<t_ind_1::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1111(lower,upper,h);
}
bool Type::empty() const {
return ind_1.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_1.getChunks(400);
}
void Type::purge() {
ind_0.clear();
ind_1.clear();
}
iterator Type::begin() const {
return ind_1.begin();
}
iterator Type::end() const {
return ind_1.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 4 direct b-tree index 0 lex-order [0,2,3]\n";
ind_0.printStats(o);
o << " arity 4 direct b-tree index 1 lex-order [0,1,2,3]\n";
ind_1.printStats(o);
}
} // namespace souffle::t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111 
namespace souffle::t_btree_000_iiii__1_0_2_3__1111__0100 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 4;
using t_tuple = Tuple<RamDomain, 4>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3])) ? -1 : (ramBitCast<RamSigned>(a[3]) > ramBitCast<RamSigned>(b[3])) ? 1 :(0))));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[3]) < ramBitCast<RamSigned>(b[3]))))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[3]) == ramBitCast<RamSigned>(b[3]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_0::iterator> lowerUpperRange_0100(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_0100(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iiii__1_0_2_3__1111__0100 
namespace souffle::t_btree_000_iiii__1_0_2_3__1111__0100 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[4];
std::copy(ramDomain, ramDomain + 4, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2,RamDomain a3) {
RamDomain data[4] = {a0,a1,a2,a3};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_0000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_1111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_1111(lower,upper,h);
}
range<t_ind_0::iterator> Type::lowerUpperRange_0100(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_0100(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_0100(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 4 direct b-tree index 0 lex-order [1,0,2,3]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_iiii__1_0_2_3__1111__0100 
namespace  souffle {
using namespace souffle;
class Stratum_CFGraph_edge_4d26e319bb257c49 {
public:
 Stratum_CFGraph_edge_4d26e319bb257c49(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type& rel_CFGraph_edge_db08b41d50d8a475,t_btree_000_ii__0_1__11::Type& rel_call_ee1d8972d66cc25f,t_btree_000_iii__0_1_2__111::Type& rel_cf_edge_4931a04c8c74bb72);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type* rel_CFGraph_edge_db08b41d50d8a475;
t_btree_000_ii__0_1__11::Type* rel_call_ee1d8972d66cc25f;
t_btree_000_iii__0_1_2__111::Type* rel_cf_edge_4931a04c8c74bb72;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_CFGraph_edge_4d26e319bb257c49::Stratum_CFGraph_edge_4d26e319bb257c49(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type& rel_CFGraph_edge_db08b41d50d8a475,t_btree_000_ii__0_1__11::Type& rel_call_ee1d8972d66cc25f,t_btree_000_iii__0_1_2__111::Type& rel_cf_edge_4931a04c8c74bb72):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_CFGraph_edge_db08b41d50d8a475(&rel_CFGraph_edge_db08b41d50d8a475),
rel_call_ee1d8972d66cc25f(&rel_call_ee1d8972d66cc25f),
rel_cf_edge_4931a04c8c74bb72(&rel_cf_edge_4931a04c8c74bb72){
}

void Stratum_CFGraph_edge_4d26e319bb257c49::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(CFGraph.edge(f,s1,f,s2) :- 
   cf_edge(f,s1,s2).
in file stack_roots.dl [77:1-77:50])_");
if(!(rel_cf_edge_4931a04c8c74bb72->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt,rel_CFGraph_edge_db08b41d50d8a475->createContext());
CREATE_OP_CONTEXT(rel_cf_edge_4931a04c8c74bb72_op_ctxt,rel_cf_edge_4931a04c8c74bb72->createContext());
for(const auto& env0 : *rel_cf_edge_4931a04c8c74bb72) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[0]),ramBitCast(env0[2])}};
rel_CFGraph_edge_db08b41d50d8a475->insert(tuple,READ_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt));
}
}
();}
signalHandler->setMsg(R"_(CFGraph.edge(f,s1,g,0) :- 
   call([f,s1],g).
in file stack_roots.dl [78:1-78:47])_");
if(!(rel_call_ee1d8972d66cc25f->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt,rel_CFGraph_edge_db08b41d50d8a475->createContext());
CREATE_OP_CONTEXT(rel_call_ee1d8972d66cc25f_op_ctxt,rel_call_ee1d8972d66cc25f->createContext());
for(const auto& env0 : *rel_call_ee1d8972d66cc25f) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
Tuple<RamDomain,4> tuple{{ramBitCast(env1[0]),ramBitCast(env1[1]),ramBitCast(env0[1]),ramBitCast(RamSigned(0))}};
rel_CFGraph_edge_db08b41d50d8a475->insert(tuple,READ_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt));
}
}
}
();}
if (pruneImdtRels) rel_call_ee1d8972d66cc25f->purge();
if (pruneImdtRels) rel_cf_edge_4931a04c8c74bb72->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_CFGraph_reachable_7410d937e4ac8127 {
public:
 Stratum_CFGraph_reachable_7410d937e4ac8127(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type& rel_delta_CFGraph_reachable_3f3bf343bbb37861,t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type& rel_new_CFGraph_reachable_c98538911662603c,t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type& rel_CFGraph_edge_db08b41d50d8a475,t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type& rel_CFGraph_reachable_c344462befee4909);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type* rel_delta_CFGraph_reachable_3f3bf343bbb37861;
t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type* rel_new_CFGraph_reachable_c98538911662603c;
t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type* rel_CFGraph_edge_db08b41d50d8a475;
t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type* rel_CFGraph_reachable_c344462befee4909;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_CFGraph_reachable_7410d937e4ac8127::Stratum_CFGraph_reachable_7410d937e4ac8127(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type& rel_delta_CFGraph_reachable_3f3bf343bbb37861,t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type& rel_new_CFGraph_reachable_c98538911662603c,t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type& rel_CFGraph_edge_db08b41d50d8a475,t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type& rel_CFGraph_reachable_c344462befee4909):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_delta_CFGraph_reachable_3f3bf343bbb37861(&rel_delta_CFGraph_reachable_3f3bf343bbb37861),
rel_new_CFGraph_reachable_c98538911662603c(&rel_new_CFGraph_reachable_c98538911662603c),
rel_CFGraph_edge_db08b41d50d8a475(&rel_CFGraph_edge_db08b41d50d8a475),
rel_CFGraph_reachable_c344462befee4909(&rel_CFGraph_reachable_c344462befee4909){
}

void Stratum_CFGraph_reachable_7410d937e4ac8127::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(CFGraph.reachable(f,s1,f,s2) :- 
   CFGraph.edge(f,s1,f,s2).
in file stack_roots.dl [20:2-20:48])_");
if(!(rel_CFGraph_edge_db08b41d50d8a475->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt,rel_CFGraph_edge_db08b41d50d8a475->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
for(const auto& env0 : *rel_CFGraph_edge_db08b41d50d8a475) {
if( (ramBitCast<RamDomain>(env0[0]) == ramBitCast<RamDomain>(env0[2]))) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[0]),ramBitCast(env0[3])}};
rel_CFGraph_reachable_c344462befee4909->insert(tuple,READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt));
}
}
}
();}
[&](){
CREATE_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt,rel_delta_CFGraph_reachable_3f3bf343bbb37861->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
for(const auto& env0 : *rel_CFGraph_reachable_c344462befee4909) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[2]),ramBitCast(env0[3])}};
rel_delta_CFGraph_reachable_3f3bf343bbb37861->insert(tuple,READ_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt));
}
}
();auto loop_counter = RamUnsigned(1);
iter = 0;
for(;;) {
signalHandler->setMsg(R"_(CFGraph.reachable(f,s1,f,s3) :- 
   CFGraph.reachable(f,s1,f,s2),
   CFGraph.edge(f,s2,f,s3).
in file stack_roots.dl [21:2-21:73])_");
if(!(rel_delta_CFGraph_reachable_3f3bf343bbb37861->empty()) && !(rel_CFGraph_edge_db08b41d50d8a475->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt,rel_delta_CFGraph_reachable_3f3bf343bbb37861->createContext());
CREATE_OP_CONTEXT(rel_new_CFGraph_reachable_c98538911662603c_op_ctxt,rel_new_CFGraph_reachable_c98538911662603c->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt,rel_CFGraph_edge_db08b41d50d8a475->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
for(const auto& env0 : *rel_delta_CFGraph_reachable_3f3bf343bbb37861) {
if( (ramBitCast<RamDomain>(env0[0]) == ramBitCast<RamDomain>(env0[2]))) {
auto range = rel_CFGraph_edge_db08b41d50d8a475->lowerUpperRange_1110(Tuple<RamDomain,4>{{ramBitCast(env0[0]), ramBitCast(env0[3]), ramBitCast(env0[0]), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast(env0[0]), ramBitCast(env0[3]), ramBitCast(env0[0]), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt));
for(const auto& env1 : range) {
if( !(rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[0]),ramBitCast(env1[3])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[0]),ramBitCast(env1[3])}};
rel_new_CFGraph_reachable_c98538911662603c->insert(tuple,READ_OP_CONTEXT(rel_new_CFGraph_reachable_c98538911662603c_op_ctxt));
}
}
}
}
}
();}
signalHandler->setMsg(R"_(CFGraph.reachable(f,s1,g,s3) :- 
   CFGraph.edge(f,s2,g,0),
   CFGraph.reachable(f,s1,f,s2),
   CFGraph.reachable(g,0,g,s3).
in file stack_roots.dl [22:2-22:96])_");
if(!(rel_delta_CFGraph_reachable_3f3bf343bbb37861->empty()) && !(rel_CFGraph_reachable_c344462befee4909->empty()) && !(rel_CFGraph_edge_db08b41d50d8a475->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt,rel_delta_CFGraph_reachable_3f3bf343bbb37861->createContext());
CREATE_OP_CONTEXT(rel_new_CFGraph_reachable_c98538911662603c_op_ctxt,rel_new_CFGraph_reachable_c98538911662603c->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt,rel_CFGraph_edge_db08b41d50d8a475->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
auto range = rel_CFGraph_edge_db08b41d50d8a475->lowerUpperRange_0001(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(RamSigned(0))}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(RamSigned(0))}},READ_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt));
for(const auto& env0 : range) {
auto range = rel_delta_CFGraph_reachable_3f3bf343bbb37861->lowerUpperRange_1011(Tuple<RamDomain,4>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[0]), ramBitCast(env0[1])}},Tuple<RamDomain,4>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[0]), ramBitCast(env0[1])}},READ_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt));
for(const auto& env1 : range) {
auto range = rel_CFGraph_reachable_c344462befee4909->lowerUpperRange_1110(Tuple<RamDomain,4>{{ramBitCast(env0[2]), ramBitCast(RamSigned(0)), ramBitCast(env0[2]), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast(env0[2]), ramBitCast(RamSigned(0)), ramBitCast(env0[2]), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt));
for(const auto& env2 : range) {
if( !(rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env0[0]),ramBitCast(env1[1]),ramBitCast(env0[2]),ramBitCast(env2[3])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt))) && !(rel_delta_CFGraph_reachable_3f3bf343bbb37861->contains(Tuple<RamDomain,4>{{ramBitCast(env0[2]),ramBitCast(RamSigned(0)),ramBitCast(env0[2]),ramBitCast(env2[3])}},READ_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env1[1]),ramBitCast(env0[2]),ramBitCast(env2[3])}};
rel_new_CFGraph_reachable_c98538911662603c->insert(tuple,READ_OP_CONTEXT(rel_new_CFGraph_reachable_c98538911662603c_op_ctxt));
}
}
}
}
}
();}
signalHandler->setMsg(R"_(CFGraph.reachable(f,s1,g,s3) :- 
   CFGraph.edge(f,s2,g,0),
   CFGraph.reachable(f,s1,f,s2),
   CFGraph.reachable(g,0,g,s3).
in file stack_roots.dl [22:2-22:96])_");
if(!(rel_CFGraph_reachable_c344462befee4909->empty()) && !(rel_delta_CFGraph_reachable_3f3bf343bbb37861->empty()) && !(rel_CFGraph_edge_db08b41d50d8a475->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt,rel_delta_CFGraph_reachable_3f3bf343bbb37861->createContext());
CREATE_OP_CONTEXT(rel_new_CFGraph_reachable_c98538911662603c_op_ctxt,rel_new_CFGraph_reachable_c98538911662603c->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt,rel_CFGraph_edge_db08b41d50d8a475->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
auto range = rel_CFGraph_edge_db08b41d50d8a475->lowerUpperRange_0001(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(RamSigned(0))}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(RamSigned(0))}},READ_OP_CONTEXT(rel_CFGraph_edge_db08b41d50d8a475_op_ctxt));
for(const auto& env0 : range) {
auto range = rel_CFGraph_reachable_c344462befee4909->lowerUpperRange_1011(Tuple<RamDomain,4>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[0]), ramBitCast(env0[1])}},Tuple<RamDomain,4>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[0]), ramBitCast(env0[1])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt));
for(const auto& env1 : range) {
auto range = rel_delta_CFGraph_reachable_3f3bf343bbb37861->lowerUpperRange_1110(Tuple<RamDomain,4>{{ramBitCast(env0[2]), ramBitCast(RamSigned(0)), ramBitCast(env0[2]), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast(env0[2]), ramBitCast(RamSigned(0)), ramBitCast(env0[2]), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_delta_CFGraph_reachable_3f3bf343bbb37861_op_ctxt));
for(const auto& env2 : range) {
if( !(rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env0[0]),ramBitCast(env1[1]),ramBitCast(env0[2]),ramBitCast(env2[3])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env1[1]),ramBitCast(env0[2]),ramBitCast(env2[3])}};
rel_new_CFGraph_reachable_c98538911662603c->insert(tuple,READ_OP_CONTEXT(rel_new_CFGraph_reachable_c98538911662603c_op_ctxt));
}
}
}
}
}
();}
if(rel_new_CFGraph_reachable_c98538911662603c->empty()) break;
[&](){
CREATE_OP_CONTEXT(rel_new_CFGraph_reachable_c98538911662603c_op_ctxt,rel_new_CFGraph_reachable_c98538911662603c->createContext());
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
for(const auto& env0 : *rel_new_CFGraph_reachable_c98538911662603c) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[2]),ramBitCast(env0[3])}};
rel_CFGraph_reachable_c344462befee4909->insert(tuple,READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt));
}
}
();std::swap(rel_delta_CFGraph_reachable_3f3bf343bbb37861, rel_new_CFGraph_reachable_c98538911662603c);
rel_new_CFGraph_reachable_c98538911662603c->purge();
loop_counter = (ramBitCast<RamUnsigned>(loop_counter) + ramBitCast<RamUnsigned>(RamUnsigned(1)));
iter++;
}
iter = 0;
rel_delta_CFGraph_reachable_3f3bf343bbb37861->purge();
rel_new_CFGraph_reachable_c98538911662603c->purge();
if (pruneImdtRels) rel_CFGraph_edge_db08b41d50d8a475->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_alias_ba5aaebc28a379e5 {
public:
 Stratum_alias_ba5aaebc28a379e5(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_delta_alias_1a64c49de7b5c1e9,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_new_alias_025151f1f7ae88b8,t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type& rel_CFGraph_reachable_c344462befee4909,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_alias_36893f0f24e80d93,t_btree_000_iii__0_1_2__111::Type& rel_assign_e4bb6e0824a16a37,t_btree_000_iiii__0_1_2_3__1111::Type& rel_bind_c9210fdc63280a40,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iiii__1_0_2_3__1111__0100::Type* rel_delta_alias_1a64c49de7b5c1e9;
t_btree_000_iiii__1_0_2_3__1111__0100::Type* rel_new_alias_025151f1f7ae88b8;
t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type* rel_CFGraph_reachable_c344462befee4909;
t_btree_000_iiii__1_0_2_3__1111__0100::Type* rel_alias_36893f0f24e80d93;
t_btree_000_iii__0_1_2__111::Type* rel_assign_e4bb6e0824a16a37;
t_btree_000_iiii__0_1_2_3__1111::Type* rel_bind_c9210fdc63280a40;
t_btree_000_ii__0_1__11::Type* rel_def_a2557aec54a7a800;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_alias_ba5aaebc28a379e5::Stratum_alias_ba5aaebc28a379e5(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_delta_alias_1a64c49de7b5c1e9,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_new_alias_025151f1f7ae88b8,t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type& rel_CFGraph_reachable_c344462befee4909,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_alias_36893f0f24e80d93,t_btree_000_iii__0_1_2__111::Type& rel_assign_e4bb6e0824a16a37,t_btree_000_iiii__0_1_2_3__1111::Type& rel_bind_c9210fdc63280a40,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_delta_alias_1a64c49de7b5c1e9(&rel_delta_alias_1a64c49de7b5c1e9),
rel_new_alias_025151f1f7ae88b8(&rel_new_alias_025151f1f7ae88b8),
rel_CFGraph_reachable_c344462befee4909(&rel_CFGraph_reachable_c344462befee4909),
rel_alias_36893f0f24e80d93(&rel_alias_36893f0f24e80d93),
rel_assign_e4bb6e0824a16a37(&rel_assign_e4bb6e0824a16a37),
rel_bind_c9210fdc63280a40(&rel_bind_c9210fdc63280a40),
rel_def_a2557aec54a7a800(&rel_def_a2557aec54a7a800){
}

void Stratum_alias_ba5aaebc28a379e5::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(alias([f,s1],$Variable(v1),[g,s2],$Member(v2, m)) :- 
   def([f,s1],$Variable(v1)),
   assign([g,s2],$Member(v2, m),$Variable(v1)),
   CFGraph.reachable(f,s1,g,s2).
in file stack_roots.dl [89:1-89:168])_");
if(!(rel_assign_e4bb6e0824a16a37->empty()) && !(rel_CFGraph_reachable_c344462befee4909->empty()) && !(rel_def_a2557aec54a7a800->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
CREATE_OP_CONTEXT(rel_assign_e4bb6e0824a16a37_op_ctxt,rel_assign_e4bb6e0824a16a37->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
for(const auto& env0 : *rel_def_a2557aec54a7a800) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
for(const auto& env3 : *rel_assign_e4bb6e0824a16a37) {
RamDomain const ref = env3[0];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env1[0]),ramBitCast(env1[1]),ramBitCast(env4[0]),ramBitCast(env4[1])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt))) {
RamDomain const ref = env3[1];
if (ref == 0) continue;
const RamDomain *env5 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env5[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env5[1];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
RamDomain const ref = env3[2];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env7[0]) == ramBitCast<RamDomain>(RamSigned(1))) && (ramBitCast<RamDomain>(env2[1]) == ramBitCast<RamDomain>(env7[1]))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env4[0])),ramBitCast(ramBitCast(env4[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env6[0])),ramBitCast(ramBitCast(env6[1]))}}
)))}}
))}};
rel_alias_36893f0f24e80d93->insert(tuple,READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Member(v1, m1),[g,s2],$Member(v2, m2)) :- 
   assign([g,s2],$Member(v2, m2),$Member(v1, m1)),
   CFGraph.reachable(f,s1,g,s2).
in file stack_roots.dl [92:1-92:145])_");
if(!(rel_assign_e4bb6e0824a16a37->empty()) && !(rel_CFGraph_reachable_c344462befee4909->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
CREATE_OP_CONTEXT(rel_assign_e4bb6e0824a16a37_op_ctxt,rel_assign_e4bb6e0824a16a37->createContext());
for(const auto& env0 : *rel_assign_e4bb6e0824a16a37) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env2[1];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env4[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env4[1];
if (ref == 0) continue;
const RamDomain *env5 = recordTable.unpack(ref,2);
{
auto range = rel_CFGraph_reachable_c344462befee4909->lowerUpperRange_0011(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env1[0]), ramBitCast(env1[1])}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env1[0]), ramBitCast(env1[1])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt));
for(const auto& env6 : range) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env6[0])),ramBitCast(ramBitCast(env6[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env5[0])),ramBitCast(ramBitCast(env5[1]))}}
)))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[0])),ramBitCast(ramBitCast(env3[1]))}}
)))}}
))}};
rel_alias_36893f0f24e80d93->insert(tuple,READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Variable(v),[g,s2],$Variable(v2)) :- 
   def([f,s1],$Variable(v)),
   assign([g,s2],$Variable(v2),$Variable(v)),
   CFGraph.reachable(f,s1,g,s2).
in file stack_roots.dl [93:1-93:163])_");
if(!(rel_assign_e4bb6e0824a16a37->empty()) && !(rel_CFGraph_reachable_c344462befee4909->empty()) && !(rel_def_a2557aec54a7a800->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
CREATE_OP_CONTEXT(rel_assign_e4bb6e0824a16a37_op_ctxt,rel_assign_e4bb6e0824a16a37->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
for(const auto& env0 : *rel_def_a2557aec54a7a800) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
for(const auto& env3 : *rel_assign_e4bb6e0824a16a37) {
RamDomain const ref = env3[0];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env1[0]),ramBitCast(env1[1]),ramBitCast(env4[0]),ramBitCast(env4[1])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt))) {
RamDomain const ref = env3[1];
if (ref == 0) continue;
const RamDomain *env5 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env5[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
RamDomain const ref = env3[2];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env6[0]) == ramBitCast<RamDomain>(RamSigned(1))) && (ramBitCast<RamDomain>(env2[1]) == ramBitCast<RamDomain>(env6[1]))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env4[0])),ramBitCast(ramBitCast(env4[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env5[1]))}}
))}};
rel_alias_36893f0f24e80d93->insert(tuple,READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Variable(v),[g,0],$Variable(v2)) :- 
   def([f,s1],$Variable(v)),
   bind([f,s2],$Variable(v),g,v2),
   CFGraph.reachable(f,s1,f,s2).
in file stack_roots.dl [94:1-94:152])_");
if(!(rel_bind_c9210fdc63280a40->empty()) && !(rel_CFGraph_reachable_c344462befee4909->empty()) && !(rel_def_a2557aec54a7a800->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
CREATE_OP_CONTEXT(rel_bind_c9210fdc63280a40_op_ctxt,rel_bind_c9210fdc63280a40->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
for(const auto& env0 : *rel_def_a2557aec54a7a800) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
for(const auto& env3 : *rel_bind_c9210fdc63280a40) {
RamDomain const ref = env3[0];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env1[0]) == ramBitCast<RamDomain>(env4[0])) && rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env1[0]),ramBitCast(env1[1]),ramBitCast(env1[0]),ramBitCast(env4[1])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt))) {
RamDomain const ref = env3[1];
if (ref == 0) continue;
const RamDomain *env5 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env5[0]) == ramBitCast<RamDomain>(RamSigned(1))) && (ramBitCast<RamDomain>(env2[1]) == ramBitCast<RamDomain>(env5[1]))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[2])),ramBitCast(ramBitCast(RamSigned(0)))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env3[3]))}}
))}};
rel_alias_36893f0f24e80d93->insert(tuple,READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
}
}
}
}
}
}
}
}
}
}
();}
[&](){
CREATE_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt,rel_delta_alias_1a64c49de7b5c1e9->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_alias_36893f0f24e80d93) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[2]),ramBitCast(env0[3])}};
rel_delta_alias_1a64c49de7b5c1e9->insert(tuple,READ_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt));
}
}
();auto loop_counter = RamUnsigned(1);
iter = 0;
for(;;) {
signalHandler->setMsg(R"_(alias([f,s1],$Variable(v1),[h,s4],$Member(v3, m)) :- 
   alias([f,s1],$Variable(v1),[g,s2],r),
   alias([g,s3],r,[h,s4],$Member(v3, m)).
in file stack_roots.dl [90:1-90:145])_");
if(!(rel_delta_alias_1a64c49de7b5c1e9->empty()) && !(rel_alias_36893f0f24e80d93->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt,rel_delta_alias_1a64c49de7b5c1e9->createContext());
CREATE_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt,rel_new_alias_025151f1f7ae88b8->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_delta_alias_1a64c49de7b5c1e9) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
auto range = rel_alias_36893f0f24e80d93->lowerUpperRange_0100(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
for(const auto& env4 : range) {
RamDomain const ref = env4[0];
if (ref == 0) continue;
const RamDomain *env5 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env3[0]) == ramBitCast<RamDomain>(env5[0]))) {
RamDomain const ref = env4[2];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
RamDomain const ref = env4[3];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env7[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env7[1];
if (ref == 0) continue;
const RamDomain *env8 = recordTable.unpack(ref,2);
{
if( !(rel_delta_alias_1a64c49de7b5c1e9->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[0])),ramBitCast(ramBitCast(env5[1]))}}
)),ramBitCast(env0[3]),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env6[0])),ramBitCast(ramBitCast(env6[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)))}}
))}},READ_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt))) && !(rel_alias_36893f0f24e80d93->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env6[0])),ramBitCast(ramBitCast(env6[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)))}}
))}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env6[0])),ramBitCast(ramBitCast(env6[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)))}}
))}};
rel_new_alias_025151f1f7ae88b8->insert(tuple,READ_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Variable(v1),[h,s4],$Member(v3, m)) :- 
   alias([f,s1],$Variable(v1),[g,s2],r),
   alias([g,s3],r,[h,s4],$Member(v3, m)).
in file stack_roots.dl [90:1-90:145])_");
if(!(rel_alias_36893f0f24e80d93->empty()) && !(rel_delta_alias_1a64c49de7b5c1e9->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt,rel_delta_alias_1a64c49de7b5c1e9->createContext());
CREATE_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt,rel_new_alias_025151f1f7ae88b8->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_alias_36893f0f24e80d93) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
auto range = rel_delta_alias_1a64c49de7b5c1e9->lowerUpperRange_0100(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt));
for(const auto& env4 : range) {
RamDomain const ref = env4[0];
if (ref == 0) continue;
const RamDomain *env5 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env3[0]) == ramBitCast<RamDomain>(env5[0]))) {
RamDomain const ref = env4[2];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
RamDomain const ref = env4[3];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env7[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env7[1];
if (ref == 0) continue;
const RamDomain *env8 = recordTable.unpack(ref,2);
{
if( !(rel_alias_36893f0f24e80d93->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env6[0])),ramBitCast(ramBitCast(env6[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)))}}
))}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env6[0])),ramBitCast(ramBitCast(env6[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)))}}
))}};
rel_new_alias_025151f1f7ae88b8->insert(tuple,READ_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Member(v1, m1),[h,s3],$Member(v2, m2)) :- 
   alias([f,s1],$Member(v1, m1),[g,s2],r),
   alias([g,s2],r,[h,s3],$Member(v2, m2)).
in file stack_roots.dl [91:1-91:151])_");
if(!(rel_delta_alias_1a64c49de7b5c1e9->empty()) && !(rel_alias_36893f0f24e80d93->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt,rel_delta_alias_1a64c49de7b5c1e9->createContext());
CREATE_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt,rel_new_alias_025151f1f7ae88b8->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_delta_alias_1a64c49de7b5c1e9) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env2[1];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
auto range = rel_alias_36893f0f24e80d93->lowerUpperRange_0100(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
for(const auto& env5 : range) {
RamDomain const ref = env5[0];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env4[1]) == ramBitCast<RamDomain>(env6[1])) && (ramBitCast<RamDomain>(env4[0]) == ramBitCast<RamDomain>(env6[0]))) {
RamDomain const ref = env5[2];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
RamDomain const ref = env5[3];
if (ref == 0) continue;
const RamDomain *env8 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env8[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env8[1];
if (ref == 0) continue;
const RamDomain *env9 = recordTable.unpack(ref,2);
{
if( !(rel_delta_alias_1a64c49de7b5c1e9->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env4[0])),ramBitCast(ramBitCast(env4[1]))}}
)),ramBitCast(env0[3]),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env7[0])),ramBitCast(ramBitCast(env7[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env9[0])),ramBitCast(ramBitCast(env9[1]))}}
)))}}
))}},READ_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt))) && !(rel_alias_36893f0f24e80d93->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[0])),ramBitCast(ramBitCast(env3[1]))}}
)))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env7[0])),ramBitCast(ramBitCast(env7[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env9[0])),ramBitCast(ramBitCast(env9[1]))}}
)))}}
))}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[0])),ramBitCast(ramBitCast(env3[1]))}}
)))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env7[0])),ramBitCast(ramBitCast(env7[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env9[0])),ramBitCast(ramBitCast(env9[1]))}}
)))}}
))}};
rel_new_alias_025151f1f7ae88b8->insert(tuple,READ_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Member(v1, m1),[h,s3],$Member(v2, m2)) :- 
   alias([f,s1],$Member(v1, m1),[g,s2],r),
   alias([g,s2],r,[h,s3],$Member(v2, m2)).
in file stack_roots.dl [91:1-91:151])_");
if(!(rel_alias_36893f0f24e80d93->empty()) && !(rel_delta_alias_1a64c49de7b5c1e9->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt,rel_delta_alias_1a64c49de7b5c1e9->createContext());
CREATE_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt,rel_new_alias_025151f1f7ae88b8->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_alias_36893f0f24e80d93) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env2[1];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
auto range = rel_delta_alias_1a64c49de7b5c1e9->lowerUpperRange_0100(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[3]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt));
for(const auto& env5 : range) {
RamDomain const ref = env5[0];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env4[1]) == ramBitCast<RamDomain>(env6[1])) && (ramBitCast<RamDomain>(env4[0]) == ramBitCast<RamDomain>(env6[0]))) {
RamDomain const ref = env5[2];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
RamDomain const ref = env5[3];
if (ref == 0) continue;
const RamDomain *env8 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env8[0]) == ramBitCast<RamDomain>(RamSigned(0)))) {
RamDomain const ref = env8[1];
if (ref == 0) continue;
const RamDomain *env9 = recordTable.unpack(ref,2);
{
if( !(rel_alias_36893f0f24e80d93->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[0])),ramBitCast(ramBitCast(env3[1]))}}
)))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env7[0])),ramBitCast(ramBitCast(env7[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env9[0])),ramBitCast(ramBitCast(env9[1]))}}
)))}}
))}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[0])),ramBitCast(ramBitCast(env3[1]))}}
)))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env7[0])),ramBitCast(ramBitCast(env7[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(0))),ramBitCast(ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env9[0])),ramBitCast(ramBitCast(env9[1]))}}
)))}}
))}};
rel_new_alias_025151f1f7ae88b8->insert(tuple,READ_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Variable(v),[g,s2],$Variable(v2)) :- 
   alias([f,s1],$Variable(v),[h,s3],$Variable(v3)),
   alias([h,s3],$Variable(v3),[g,s2],$Variable(v2)).
in file stack_roots.dl [95:1-95:165])_");
if(!(rel_delta_alias_1a64c49de7b5c1e9->empty()) && !(rel_alias_36893f0f24e80d93->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt,rel_delta_alias_1a64c49de7b5c1e9->createContext());
CREATE_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt,rel_new_alias_025151f1f7ae88b8->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_delta_alias_1a64c49de7b5c1e9) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[3];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env4[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
for(const auto& env5 : *rel_alias_36893f0f24e80d93) {
RamDomain const ref = env5[0];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env3[1]) == ramBitCast<RamDomain>(env6[1])) && (ramBitCast<RamDomain>(env3[0]) == ramBitCast<RamDomain>(env6[0]))) {
RamDomain const ref = env5[1];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env7[0]) == ramBitCast<RamDomain>(RamSigned(1))) && (ramBitCast<RamDomain>(env4[1]) == ramBitCast<RamDomain>(env7[1]))) {
RamDomain const ref = env5[2];
if (ref == 0) continue;
const RamDomain *env8 = recordTable.unpack(ref,2);
{
RamDomain const ref = env5[3];
if (ref == 0) continue;
const RamDomain *env9 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env9[0]) == ramBitCast<RamDomain>(RamSigned(1))) && !(rel_alias_36893f0f24e80d93->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env9[1]))}}
))}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt))) && !(rel_delta_alias_1a64c49de7b5c1e9->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env3[0])),ramBitCast(ramBitCast(env3[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env4[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env9[1]))}}
))}},READ_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env9[1]))}}
))}};
rel_new_alias_025151f1f7ae88b8->insert(tuple,READ_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(alias([f,s1],$Variable(v),[g,s2],$Variable(v2)) :- 
   alias([f,s1],$Variable(v),[h,s3],$Variable(v3)),
   alias([h,s3],$Variable(v3),[g,s2],$Variable(v2)).
in file stack_roots.dl [95:1-95:165])_");
if(!(rel_alias_36893f0f24e80d93->empty()) && !(rel_delta_alias_1a64c49de7b5c1e9->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_alias_1a64c49de7b5c1e9_op_ctxt,rel_delta_alias_1a64c49de7b5c1e9->createContext());
CREATE_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt,rel_new_alias_025151f1f7ae88b8->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_alias_36893f0f24e80d93) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[3];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env4[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
for(const auto& env5 : *rel_delta_alias_1a64c49de7b5c1e9) {
RamDomain const ref = env5[0];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env3[1]) == ramBitCast<RamDomain>(env6[1])) && (ramBitCast<RamDomain>(env3[0]) == ramBitCast<RamDomain>(env6[0]))) {
RamDomain const ref = env5[1];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env7[0]) == ramBitCast<RamDomain>(RamSigned(1))) && (ramBitCast<RamDomain>(env4[1]) == ramBitCast<RamDomain>(env7[1]))) {
RamDomain const ref = env5[2];
if (ref == 0) continue;
const RamDomain *env8 = recordTable.unpack(ref,2);
{
RamDomain const ref = env5[3];
if (ref == 0) continue;
const RamDomain *env9 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env9[0]) == ramBitCast<RamDomain>(RamSigned(1))) && !(rel_alias_36893f0f24e80d93->contains(Tuple<RamDomain,4>{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env9[1]))}}
))}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt)))) {
Tuple<RamDomain,4> tuple{{ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env1[0])),ramBitCast(ramBitCast(env1[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env2[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(env8[0])),ramBitCast(ramBitCast(env8[1]))}}
)),ramBitCast(pack(recordTable,Tuple<RamDomain,2>{{ramBitCast(ramBitCast(RamSigned(1))),ramBitCast(ramBitCast(env9[1]))}}
))}};
rel_new_alias_025151f1f7ae88b8->insert(tuple,READ_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
if(rel_new_alias_025151f1f7ae88b8->empty()) break;
[&](){
CREATE_OP_CONTEXT(rel_new_alias_025151f1f7ae88b8_op_ctxt,rel_new_alias_025151f1f7ae88b8->createContext());
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
for(const auto& env0 : *rel_new_alias_025151f1f7ae88b8) {
Tuple<RamDomain,4> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[2]),ramBitCast(env0[3])}};
rel_alias_36893f0f24e80d93->insert(tuple,READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
}
}
();std::swap(rel_delta_alias_1a64c49de7b5c1e9, rel_new_alias_025151f1f7ae88b8);
rel_new_alias_025151f1f7ae88b8->purge();
loop_counter = (ramBitCast<RamUnsigned>(loop_counter) + ramBitCast<RamUnsigned>(RamUnsigned(1)));
iter++;
}
iter = 0;
rel_delta_alias_1a64c49de7b5c1e9->purge();
rel_new_alias_025151f1f7ae88b8->purge();
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","a\tvf\tb\tvg"},{"auxArity","0"},{"name","alias"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 4, \"params\": [\"a\", \"vf\", \"b\", \"vg\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 4, \"types\": [\"r:Location\", \"+:Reference\", \"r:Location\", \"+:Reference\"]}}"}});
if (outputDirectory == "-"){directiveMap["IO"] = "stdout"; directiveMap["headers"] = "true";}
else if (!outputDirectory.empty()) {directiveMap["output-dir"] = outputDirectory;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_alias_36893f0f24e80d93);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}
if (pruneImdtRels) rel_assign_e4bb6e0824a16a37->purge();
if (pruneImdtRels) rel_bind_c9210fdc63280a40->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_aliasUsed_ac6b34bca10a1e2d {
public:
 Stratum_aliasUsed_ac6b34bca10a1e2d(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_alias_36893f0f24e80d93,t_btree_000_ii__0_1__11::Type& rel_aliasUsed_65edfdff09a886e0,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800,t_btree_000_ii__1_0__11__01::Type& rel_use_e955e932f22dad4d);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iiii__1_0_2_3__1111__0100::Type* rel_alias_36893f0f24e80d93;
t_btree_000_ii__0_1__11::Type* rel_aliasUsed_65edfdff09a886e0;
t_btree_000_ii__0_1__11::Type* rel_def_a2557aec54a7a800;
t_btree_000_ii__1_0__11__01::Type* rel_use_e955e932f22dad4d;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_aliasUsed_ac6b34bca10a1e2d::Stratum_aliasUsed_ac6b34bca10a1e2d(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__1_0_2_3__1111__0100::Type& rel_alias_36893f0f24e80d93,t_btree_000_ii__0_1__11::Type& rel_aliasUsed_65edfdff09a886e0,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800,t_btree_000_ii__1_0__11__01::Type& rel_use_e955e932f22dad4d):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_alias_36893f0f24e80d93(&rel_alias_36893f0f24e80d93),
rel_aliasUsed_65edfdff09a886e0(&rel_aliasUsed_65edfdff09a886e0),
rel_def_a2557aec54a7a800(&rel_def_a2557aec54a7a800),
rel_use_e955e932f22dad4d(&rel_use_e955e932f22dad4d){
}

void Stratum_aliasUsed_ac6b34bca10a1e2d::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(aliasUsed(f,r) :- 
   alias([f,_<unnamed_1>],r,[g,_<unnamed_2>],r2),
   use([g,_<unnamed_3>],r2).
in file stack_roots.dl [97:1-97:66])_");
if(!(rel_alias_36893f0f24e80d93->empty()) && !(rel_use_e955e932f22dad4d->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
CREATE_OP_CONTEXT(rel_aliasUsed_65edfdff09a886e0_op_ctxt,rel_aliasUsed_65edfdff09a886e0->createContext());
CREATE_OP_CONTEXT(rel_use_e955e932f22dad4d_op_ctxt,rel_use_e955e932f22dad4d->createContext());
for(const auto& env0 : *rel_alias_36893f0f24e80d93) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[2];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
auto range = rel_use_e955e932f22dad4d->lowerUpperRange_01(Tuple<RamDomain,2>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[3])}},Tuple<RamDomain,2>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[3])}},READ_OP_CONTEXT(rel_use_e955e932f22dad4d_op_ctxt));
for(const auto& env3 : range) {
RamDomain const ref = env3[0];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(env4[0]))) {
Tuple<RamDomain,2> tuple{{ramBitCast(env1[0]),ramBitCast(env0[1])}};
rel_aliasUsed_65edfdff09a886e0->insert(tuple,READ_OP_CONTEXT(rel_aliasUsed_65edfdff09a886e0_op_ctxt));
}
}
}
}
}
}
}
();}
signalHandler->setMsg(R"_(aliasUsed(f,r) :- 
   def([f,_<unnamed_1>],r),
   alias([f,_<unnamed_2>],r,_,r2),
   use(_,r2).
in file stack_roots.dl [98:1-98:72])_");
if(!(rel_alias_36893f0f24e80d93->empty()) && !(rel_use_e955e932f22dad4d->empty()) && !(rel_def_a2557aec54a7a800->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt,rel_alias_36893f0f24e80d93->createContext());
CREATE_OP_CONTEXT(rel_aliasUsed_65edfdff09a886e0_op_ctxt,rel_aliasUsed_65edfdff09a886e0->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
CREATE_OP_CONTEXT(rel_use_e955e932f22dad4d_op_ctxt,rel_use_e955e932f22dad4d->createContext());
for(const auto& env0 : *rel_def_a2557aec54a7a800) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
auto range = rel_alias_36893f0f24e80d93->lowerUpperRange_0100(Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[1]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,4>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[1]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_alias_36893f0f24e80d93_op_ctxt));
for(const auto& env2 : range) {
if( !rel_use_e955e932f22dad4d->lowerUpperRange_01(Tuple<RamDomain,2>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env2[3])}},Tuple<RamDomain,2>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env2[3])}},READ_OP_CONTEXT(rel_use_e955e932f22dad4d_op_ctxt)).empty()) {
RamDomain const ref = env2[0];
if (ref == 0) continue;
const RamDomain *env3 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env1[0]) == ramBitCast<RamDomain>(env3[0]))) {
Tuple<RamDomain,2> tuple{{ramBitCast(env1[0]),ramBitCast(env0[1])}};
rel_aliasUsed_65edfdff09a886e0->insert(tuple,READ_OP_CONTEXT(rel_aliasUsed_65edfdff09a886e0_op_ctxt));
}
}
}
}
}
}
}
();}
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tv"},{"auxArity","0"},{"name","aliasUsed"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"+:Reference\"]}}"}});
if (outputDirectory == "-"){directiveMap["IO"] = "stdout"; directiveMap["headers"] = "true";}
else if (!outputDirectory.empty()) {directiveMap["output-dir"] = outputDirectory;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_aliasUsed_65edfdff09a886e0);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}
if (pruneImdtRels) rel_def_a2557aec54a7a800->purge();
if (pruneImdtRels) rel_use_e955e932f22dad4d->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_assign_e0d78e44f4df6411 {
public:
 Stratum_assign_e0d78e44f4df6411(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_assign_e4bb6e0824a16a37);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_1_2__111::Type* rel_assign_e4bb6e0824a16a37;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_assign_e0d78e44f4df6411::Stratum_assign_e0d78e44f4df6411(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_assign_e4bb6e0824a16a37):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_assign_e4bb6e0824a16a37(&rel_assign_e4bb6e0824a16a37){
}

void Stratum_assign_e0d78e44f4df6411::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc\tx\ty"},{"auxArity","0"},{"fact-dir","."},{"name","assign"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 3, \"params\": [\"loc\", \"x\", \"y\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 3, \"types\": [\"r:Location\", \"+:Reference\", \"+:Reference\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_assign_e4bb6e0824a16a37);
} catch (std::exception& e) {std::cerr << "Error loading assign data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_bind_8b0da46e2379b6cd {
public:
 Stratum_bind_8b0da46e2379b6cd(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__0_1_2_3__1111::Type& rel_bind_c9210fdc63280a40);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iiii__0_1_2_3__1111::Type* rel_bind_c9210fdc63280a40;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_bind_8b0da46e2379b6cd::Stratum_bind_8b0da46e2379b6cd(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__0_1_2_3__1111::Type& rel_bind_c9210fdc63280a40):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_bind_c9210fdc63280a40(&rel_bind_c9210fdc63280a40){
}

void Stratum_bind_8b0da46e2379b6cd::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","caller\tcaller_arg\tcallee\tcallee_arg"},{"auxArity","0"},{"fact-dir","."},{"name","bind"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 4, \"params\": [\"caller\", \"caller_arg\", \"callee\", \"callee_arg\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 4, \"types\": [\"r:Location\", \"+:Reference\", \"s:Function\", \"s:symbol\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_bind_c9210fdc63280a40);
} catch (std::exception& e) {std::cerr << "Error loading bind data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_call_104fac07831e2229 {
public:
 Stratum_call_104fac07831e2229(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_ii__0_1__11::Type& rel_call_ee1d8972d66cc25f);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_ii__0_1__11::Type* rel_call_ee1d8972d66cc25f;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_call_104fac07831e2229::Stratum_call_104fac07831e2229(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_ii__0_1__11::Type& rel_call_ee1d8972d66cc25f):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_call_ee1d8972d66cc25f(&rel_call_ee1d8972d66cc25f){
}

void Stratum_call_104fac07831e2229::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","caller\tcallee"},{"auxArity","0"},{"fact-dir","."},{"name","call"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"caller\", \"callee\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"r:Location\", \"s:Function\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_call_ee1d8972d66cc25f);
} catch (std::exception& e) {std::cerr << "Error loading call data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_cf_edge_c2ae152829fd6f1f {
public:
 Stratum_cf_edge_c2ae152829fd6f1f(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_cf_edge_4931a04c8c74bb72);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_1_2__111::Type* rel_cf_edge_4931a04c8c74bb72;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_cf_edge_c2ae152829fd6f1f::Stratum_cf_edge_c2ae152829fd6f1f(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_cf_edge_4931a04c8c74bb72):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_cf_edge_4931a04c8c74bb72(&rel_cf_edge_4931a04c8c74bb72){
}

void Stratum_cf_edge_c2ae152829fd6f1f::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\ty"},{"auxArity","0"},{"fact-dir","."},{"name","cf_edge"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"y\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"i:Statement\", \"i:Statement\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_cf_edge_4931a04c8c74bb72);
} catch (std::exception& e) {std::cerr << "Error loading cf_edge data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_collect_77936cd6fddc6c8c {
public:
 Stratum_collect_77936cd6fddc6c8c(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_i__0__1::Type& rel_collect_092686b367d9983d);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_i__0__1::Type* rel_collect_092686b367d9983d;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_collect_77936cd6fddc6c8c::Stratum_collect_77936cd6fddc6c8c(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_i__0__1::Type& rel_collect_092686b367d9983d):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_collect_092686b367d9983d(&rel_collect_092686b367d9983d){
}

void Stratum_collect_77936cd6fddc6c8c::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc"},{"auxArity","0"},{"fact-dir","."},{"name","collect"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 1, \"params\": [\"loc\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 1, \"types\": [\"r:Location\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_collect_092686b367d9983d);
} catch (std::exception& e) {std::cerr << "Error loading collect data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_def_6f7db9860aa6b531 {
public:
 Stratum_def_6f7db9860aa6b531(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_assign_e4bb6e0824a16a37,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_1_2__111::Type* rel_assign_e4bb6e0824a16a37;
t_btree_000_ii__0_1__11::Type* rel_def_a2557aec54a7a800;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_def_6f7db9860aa6b531::Stratum_def_6f7db9860aa6b531(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_assign_e4bb6e0824a16a37,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_assign_e4bb6e0824a16a37(&rel_assign_e4bb6e0824a16a37),
rel_def_a2557aec54a7a800(&rel_def_a2557aec54a7a800){
}

void Stratum_def_6f7db9860aa6b531::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc\tv"},{"auxArity","0"},{"fact-dir","."},{"name","def"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"loc\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"r:Location\", \"+:Reference\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_def_a2557aec54a7a800);
} catch (std::exception& e) {std::cerr << "Error loading def data: " << e.what() << '\n';
exit(1);
}
}
signalHandler->setMsg(R"_(def(l,r) :- 
   assign(l,r,_).
in file stack_roots.dl [100:1-100:30])_");
if(!(rel_assign_e4bb6e0824a16a37->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_assign_e4bb6e0824a16a37_op_ctxt,rel_assign_e4bb6e0824a16a37->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
for(const auto& env0 : *rel_assign_e4bb6e0824a16a37) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_def_a2557aec54a7a800->insert(tuple,READ_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt));
}
}
();}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_root_vars_d910841585fde373 {
public:
 Stratum_root_vars_d910841585fde373(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type& rel_CFGraph_reachable_c344462befee4909,t_btree_000_i__0__1::Type& rel_collect_092686b367d9983d,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800,t_btree_000_ii__0_1__11::Type& rel_root_vars_9dd5ee9984886e0d,t_btree_000_ii__1_0__11__01::Type& rel_use_e955e932f22dad4d);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type* rel_CFGraph_reachable_c344462befee4909;
t_btree_000_i__0__1::Type* rel_collect_092686b367d9983d;
t_btree_000_ii__0_1__11::Type* rel_def_a2557aec54a7a800;
t_btree_000_ii__0_1__11::Type* rel_root_vars_9dd5ee9984886e0d;
t_btree_000_ii__1_0__11__01::Type* rel_use_e955e932f22dad4d;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_root_vars_d910841585fde373::Stratum_root_vars_d910841585fde373(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type& rel_CFGraph_reachable_c344462befee4909,t_btree_000_i__0__1::Type& rel_collect_092686b367d9983d,t_btree_000_ii__0_1__11::Type& rel_def_a2557aec54a7a800,t_btree_000_ii__0_1__11::Type& rel_root_vars_9dd5ee9984886e0d,t_btree_000_ii__1_0__11__01::Type& rel_use_e955e932f22dad4d):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_CFGraph_reachable_c344462befee4909(&rel_CFGraph_reachable_c344462befee4909),
rel_collect_092686b367d9983d(&rel_collect_092686b367d9983d),
rel_def_a2557aec54a7a800(&rel_def_a2557aec54a7a800),
rel_root_vars_9dd5ee9984886e0d(&rel_root_vars_9dd5ee9984886e0d),
rel_use_e955e932f22dad4d(&rel_use_e955e932f22dad4d){
}

void Stratum_root_vars_d910841585fde373::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(root_vars(f,v) :- 
   def([f,x],$Variable(v)),
   collect([f,y]),
   use([f,z],$Variable(v)),
   CFGraph.reachable(f,x,f,y),
   CFGraph.reachable(f,y,f,z).
in file stack_roots.dl [82:1-87:32])_");
if(!(rel_use_e955e932f22dad4d->empty()) && !(rel_def_a2557aec54a7a800->empty()) && !(rel_CFGraph_reachable_c344462befee4909->empty()) && !(rel_collect_092686b367d9983d->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt,rel_CFGraph_reachable_c344462befee4909->createContext());
CREATE_OP_CONTEXT(rel_collect_092686b367d9983d_op_ctxt,rel_collect_092686b367d9983d->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
CREATE_OP_CONTEXT(rel_root_vars_9dd5ee9984886e0d_op_ctxt,rel_root_vars_9dd5ee9984886e0d->createContext());
CREATE_OP_CONTEXT(rel_use_e955e932f22dad4d_op_ctxt,rel_use_e955e932f22dad4d->createContext());
for(const auto& env0 : *rel_def_a2557aec54a7a800) {
RamDomain const ref = env0[0];
if (ref == 0) continue;
const RamDomain *env1 = recordTable.unpack(ref,2);
{
RamDomain const ref = env0[1];
if (ref == 0) continue;
const RamDomain *env2 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env2[0]) == ramBitCast<RamDomain>(RamSigned(1)))) {
for(const auto& env3 : *rel_collect_092686b367d9983d) {
RamDomain const ref = env3[0];
if (ref == 0) continue;
const RamDomain *env4 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env1[0]) == ramBitCast<RamDomain>(env4[0])) && rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env1[0]),ramBitCast(env1[1]),ramBitCast(env1[0]),ramBitCast(env4[1])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt))) {
for(const auto& env5 : *rel_use_e955e932f22dad4d) {
RamDomain const ref = env5[0];
if (ref == 0) continue;
const RamDomain *env6 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env1[0]) == ramBitCast<RamDomain>(env6[0])) && rel_CFGraph_reachable_c344462befee4909->contains(Tuple<RamDomain,4>{{ramBitCast(env1[0]),ramBitCast(env4[1]),ramBitCast(env1[0]),ramBitCast(env6[1])}},READ_OP_CONTEXT(rel_CFGraph_reachable_c344462befee4909_op_ctxt))) {
RamDomain const ref = env5[1];
if (ref == 0) continue;
const RamDomain *env7 = recordTable.unpack(ref,2);
{
if( (ramBitCast<RamDomain>(env7[0]) == ramBitCast<RamDomain>(RamSigned(1))) && (ramBitCast<RamDomain>(env2[1]) == ramBitCast<RamDomain>(env7[1]))) {
Tuple<RamDomain,2> tuple{{ramBitCast(env1[0]),ramBitCast(env2[1])}};
rel_root_vars_9dd5ee9984886e0d->insert(tuple,READ_OP_CONTEXT(rel_root_vars_9dd5ee9984886e0d_op_ctxt));
}
}
}
}
}
}
}
}
}
}
}
}
}
();}
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tv"},{"auxArity","0"},{"name","root_vars"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"s:symbol\"]}}"}});
if (outputDirectory == "-"){directiveMap["IO"] = "stdout"; directiveMap["headers"] = "true";}
else if (!outputDirectory.empty()) {directiveMap["output-dir"] = outputDirectory;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_root_vars_9dd5ee9984886e0d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}
if (pruneImdtRels) rel_CFGraph_reachable_c344462befee4909->purge();
if (pruneImdtRels) rel_collect_092686b367d9983d->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_use_f38e4ba456a0cc9a {
public:
 Stratum_use_f38e4ba456a0cc9a(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_ii__1_0__11__01::Type& rel_use_e955e932f22dad4d);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_ii__1_0__11__01::Type* rel_use_e955e932f22dad4d;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_use_f38e4ba456a0cc9a::Stratum_use_f38e4ba456a0cc9a(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_ii__1_0__11__01::Type& rel_use_e955e932f22dad4d):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_use_e955e932f22dad4d(&rel_use_e955e932f22dad4d){
}

void Stratum_use_f38e4ba456a0cc9a::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc\tv"},{"auxArity","0"},{"fact-dir","."},{"name","use"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"loc\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"r:Location\", \"+:Reference\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_use_e955e932f22dad4d);
} catch (std::exception& e) {std::cerr << "Error loading use data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Sf_stack_roots: public SouffleProgram {
public:
 Sf_stack_roots();
 ~Sf_stack_roots();
void run();
void runAll(std::string inputDirectoryArg = "",std::string outputDirectoryArg = "",bool performIOArg = true,bool pruneImdtRelsArg = true);
void printAll([[maybe_unused]] std::string outputDirectoryArg = "");
void loadAll([[maybe_unused]] std::string inputDirectoryArg = "");
void dumpInputs();
void dumpOutputs();
SymbolTable& getSymbolTable();
RecordTable& getRecordTable();
void setNumThreads(std::size_t numThreadsValue);
void executeSubroutine(std::string name,const std::vector<RamDomain>& args,std::vector<RamDomain>& ret);
private:
void runFunction(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg);
SymbolTableImpl symTable;
SpecializedRecordTable<0,2> recordTable;
ConcurrentCache<std::string,std::regex> regexCache;
Own<t_btree_000_iii__0_1_2__111::Type> rel_assign_e4bb6e0824a16a37;
souffle::RelationWrapper<t_btree_000_iii__0_1_2__111::Type> wrapper_rel_assign_e4bb6e0824a16a37;
Own<t_btree_000_iiii__0_1_2_3__1111::Type> rel_bind_c9210fdc63280a40;
souffle::RelationWrapper<t_btree_000_iiii__0_1_2_3__1111::Type> wrapper_rel_bind_c9210fdc63280a40;
Own<t_btree_000_ii__0_1__11::Type> rel_call_ee1d8972d66cc25f;
souffle::RelationWrapper<t_btree_000_ii__0_1__11::Type> wrapper_rel_call_ee1d8972d66cc25f;
Own<t_btree_000_iii__0_1_2__111::Type> rel_cf_edge_4931a04c8c74bb72;
souffle::RelationWrapper<t_btree_000_iii__0_1_2__111::Type> wrapper_rel_cf_edge_4931a04c8c74bb72;
Own<t_btree_000_i__0__1::Type> rel_collect_092686b367d9983d;
souffle::RelationWrapper<t_btree_000_i__0__1::Type> wrapper_rel_collect_092686b367d9983d;
Own<t_btree_000_ii__1_0__11__01::Type> rel_use_e955e932f22dad4d;
souffle::RelationWrapper<t_btree_000_ii__1_0__11__01::Type> wrapper_rel_use_e955e932f22dad4d;
Own<t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type> rel_CFGraph_edge_db08b41d50d8a475;
souffle::RelationWrapper<t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type> wrapper_rel_CFGraph_edge_db08b41d50d8a475;
Own<t_btree_000_ii__0_1__11::Type> rel_def_a2557aec54a7a800;
souffle::RelationWrapper<t_btree_000_ii__0_1__11::Type> wrapper_rel_def_a2557aec54a7a800;
Own<t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type> rel_CFGraph_reachable_c344462befee4909;
souffle::RelationWrapper<t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type> wrapper_rel_CFGraph_reachable_c344462befee4909;
Own<t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type> rel_new_CFGraph_reachable_c98538911662603c;
Own<t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type> rel_delta_CFGraph_reachable_3f3bf343bbb37861;
Own<t_btree_000_iiii__1_0_2_3__1111__0100::Type> rel_alias_36893f0f24e80d93;
souffle::RelationWrapper<t_btree_000_iiii__1_0_2_3__1111__0100::Type> wrapper_rel_alias_36893f0f24e80d93;
Own<t_btree_000_iiii__1_0_2_3__1111__0100::Type> rel_new_alias_025151f1f7ae88b8;
Own<t_btree_000_iiii__1_0_2_3__1111__0100::Type> rel_delta_alias_1a64c49de7b5c1e9;
Own<t_btree_000_ii__0_1__11::Type> rel_root_vars_9dd5ee9984886e0d;
souffle::RelationWrapper<t_btree_000_ii__0_1__11::Type> wrapper_rel_root_vars_9dd5ee9984886e0d;
Own<t_btree_000_ii__0_1__11::Type> rel_aliasUsed_65edfdff09a886e0;
souffle::RelationWrapper<t_btree_000_ii__0_1__11::Type> wrapper_rel_aliasUsed_65edfdff09a886e0;
Stratum_CFGraph_edge_4d26e319bb257c49 stratum_CFGraph_edge_656704795f0096ba;
Stratum_CFGraph_reachable_7410d937e4ac8127 stratum_CFGraph_reachable_a1359c86b6f7bd73;
Stratum_alias_ba5aaebc28a379e5 stratum_alias_0179d0f4f86c77c2;
Stratum_aliasUsed_ac6b34bca10a1e2d stratum_aliasUsed_7d447e0118863465;
Stratum_assign_e0d78e44f4df6411 stratum_assign_f550d366a9215d2a;
Stratum_bind_8b0da46e2379b6cd stratum_bind_1968829e9243d389;
Stratum_call_104fac07831e2229 stratum_call_587d2d7effb5d130;
Stratum_cf_edge_c2ae152829fd6f1f stratum_cf_edge_4017fef287699967;
Stratum_collect_77936cd6fddc6c8c stratum_collect_e5356b85e8033273;
Stratum_def_6f7db9860aa6b531 stratum_def_1d1da3266d2fd4ce;
Stratum_root_vars_d910841585fde373 stratum_root_vars_19aeb1b6f3a71208;
Stratum_use_f38e4ba456a0cc9a stratum_use_2e20cb5441769259;
std::string inputDirectory;
std::string outputDirectory;
SignalHandler* signalHandler{SignalHandler::instance()};
std::atomic<RamDomain> ctr{};
std::atomic<std::size_t> iter{};
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Sf_stack_roots::Sf_stack_roots():
symTable(),
recordTable(),
regexCache(),
rel_assign_e4bb6e0824a16a37(mk<t_btree_000_iii__0_1_2__111::Type>()),
wrapper_rel_assign_e4bb6e0824a16a37(0, *rel_assign_e4bb6e0824a16a37, *this, "assign", std::array<const char *,3>{{"r:Location","+:Reference","+:Reference"}}, std::array<const char *,3>{{"loc","x","y"}}, 0),
rel_bind_c9210fdc63280a40(mk<t_btree_000_iiii__0_1_2_3__1111::Type>()),
wrapper_rel_bind_c9210fdc63280a40(1, *rel_bind_c9210fdc63280a40, *this, "bind", std::array<const char *,4>{{"r:Location","+:Reference","s:Function","s:symbol"}}, std::array<const char *,4>{{"caller","caller_arg","callee","callee_arg"}}, 0),
rel_call_ee1d8972d66cc25f(mk<t_btree_000_ii__0_1__11::Type>()),
wrapper_rel_call_ee1d8972d66cc25f(2, *rel_call_ee1d8972d66cc25f, *this, "call", std::array<const char *,2>{{"r:Location","s:Function"}}, std::array<const char *,2>{{"caller","callee"}}, 0),
rel_cf_edge_4931a04c8c74bb72(mk<t_btree_000_iii__0_1_2__111::Type>()),
wrapper_rel_cf_edge_4931a04c8c74bb72(3, *rel_cf_edge_4931a04c8c74bb72, *this, "cf_edge", std::array<const char *,3>{{"s:Function","i:Statement","i:Statement"}}, std::array<const char *,3>{{"f","x","y"}}, 0),
rel_collect_092686b367d9983d(mk<t_btree_000_i__0__1::Type>()),
wrapper_rel_collect_092686b367d9983d(4, *rel_collect_092686b367d9983d, *this, "collect", std::array<const char *,1>{{"r:Location"}}, std::array<const char *,1>{{"loc"}}, 0),
rel_use_e955e932f22dad4d(mk<t_btree_000_ii__1_0__11__01::Type>()),
wrapper_rel_use_e955e932f22dad4d(5, *rel_use_e955e932f22dad4d, *this, "use", std::array<const char *,2>{{"r:Location","+:Reference"}}, std::array<const char *,2>{{"loc","v"}}, 0),
rel_CFGraph_edge_db08b41d50d8a475(mk<t_btree_000_iiii__0_1_2__3_0_1_2__1110__1111__0001::Type>()),
wrapper_rel_CFGraph_edge_db08b41d50d8a475(6, *rel_CFGraph_edge_db08b41d50d8a475, *this, "CFGraph.edge", std::array<const char *,4>{{"s:Function","i:Statement","s:Function","i:Statement"}}, std::array<const char *,4>{{"f","u","g","v"}}, 0),
rel_def_a2557aec54a7a800(mk<t_btree_000_ii__0_1__11::Type>()),
wrapper_rel_def_a2557aec54a7a800(7, *rel_def_a2557aec54a7a800, *this, "def", std::array<const char *,2>{{"r:Location","+:Reference"}}, std::array<const char *,2>{{"loc","v"}}, 0),
rel_CFGraph_reachable_c344462befee4909(mk<t_btree_000_iiii__2_3_0__0_1_2_3__1011__1110__1111__0011::Type>()),
wrapper_rel_CFGraph_reachable_c344462befee4909(8, *rel_CFGraph_reachable_c344462befee4909, *this, "CFGraph.reachable", std::array<const char *,4>{{"s:Function","i:Statement","s:Function","i:Statement"}}, std::array<const char *,4>{{"f","u","g","v"}}, 0),
rel_new_CFGraph_reachable_c98538911662603c(mk<t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type>()),
rel_delta_CFGraph_reachable_3f3bf343bbb37861(mk<t_btree_000_iiii__0_2_3__0_1_2_3__1011__1110__1111::Type>()),
rel_alias_36893f0f24e80d93(mk<t_btree_000_iiii__1_0_2_3__1111__0100::Type>()),
wrapper_rel_alias_36893f0f24e80d93(9, *rel_alias_36893f0f24e80d93, *this, "alias", std::array<const char *,4>{{"r:Location","+:Reference","r:Location","+:Reference"}}, std::array<const char *,4>{{"a","vf","b","vg"}}, 0),
rel_new_alias_025151f1f7ae88b8(mk<t_btree_000_iiii__1_0_2_3__1111__0100::Type>()),
rel_delta_alias_1a64c49de7b5c1e9(mk<t_btree_000_iiii__1_0_2_3__1111__0100::Type>()),
rel_root_vars_9dd5ee9984886e0d(mk<t_btree_000_ii__0_1__11::Type>()),
wrapper_rel_root_vars_9dd5ee9984886e0d(10, *rel_root_vars_9dd5ee9984886e0d, *this, "root_vars", std::array<const char *,2>{{"s:Function","s:symbol"}}, std::array<const char *,2>{{"f","v"}}, 0),
rel_aliasUsed_65edfdff09a886e0(mk<t_btree_000_ii__0_1__11::Type>()),
wrapper_rel_aliasUsed_65edfdff09a886e0(11, *rel_aliasUsed_65edfdff09a886e0, *this, "aliasUsed", std::array<const char *,2>{{"s:Function","+:Reference"}}, std::array<const char *,2>{{"f","v"}}, 0),
stratum_CFGraph_edge_656704795f0096ba(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_CFGraph_edge_db08b41d50d8a475,*rel_call_ee1d8972d66cc25f,*rel_cf_edge_4931a04c8c74bb72),
stratum_CFGraph_reachable_a1359c86b6f7bd73(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_delta_CFGraph_reachable_3f3bf343bbb37861,*rel_new_CFGraph_reachable_c98538911662603c,*rel_CFGraph_edge_db08b41d50d8a475,*rel_CFGraph_reachable_c344462befee4909),
stratum_alias_0179d0f4f86c77c2(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_delta_alias_1a64c49de7b5c1e9,*rel_new_alias_025151f1f7ae88b8,*rel_CFGraph_reachable_c344462befee4909,*rel_alias_36893f0f24e80d93,*rel_assign_e4bb6e0824a16a37,*rel_bind_c9210fdc63280a40,*rel_def_a2557aec54a7a800),
stratum_aliasUsed_7d447e0118863465(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_alias_36893f0f24e80d93,*rel_aliasUsed_65edfdff09a886e0,*rel_def_a2557aec54a7a800,*rel_use_e955e932f22dad4d),
stratum_assign_f550d366a9215d2a(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_assign_e4bb6e0824a16a37),
stratum_bind_1968829e9243d389(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_bind_c9210fdc63280a40),
stratum_call_587d2d7effb5d130(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_call_ee1d8972d66cc25f),
stratum_cf_edge_4017fef287699967(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_cf_edge_4931a04c8c74bb72),
stratum_collect_e5356b85e8033273(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_collect_092686b367d9983d),
stratum_def_1d1da3266d2fd4ce(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_assign_e4bb6e0824a16a37,*rel_def_a2557aec54a7a800),
stratum_root_vars_19aeb1b6f3a71208(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_CFGraph_reachable_c344462befee4909,*rel_collect_092686b367d9983d,*rel_def_a2557aec54a7a800,*rel_root_vars_9dd5ee9984886e0d,*rel_use_e955e932f22dad4d),
stratum_use_2e20cb5441769259(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_use_e955e932f22dad4d){
addRelation("assign", wrapper_rel_assign_e4bb6e0824a16a37, true, false);
addRelation("bind", wrapper_rel_bind_c9210fdc63280a40, true, false);
addRelation("call", wrapper_rel_call_ee1d8972d66cc25f, true, false);
addRelation("cf_edge", wrapper_rel_cf_edge_4931a04c8c74bb72, true, false);
addRelation("collect", wrapper_rel_collect_092686b367d9983d, true, false);
addRelation("use", wrapper_rel_use_e955e932f22dad4d, true, false);
addRelation("CFGraph.edge", wrapper_rel_CFGraph_edge_db08b41d50d8a475, false, false);
addRelation("def", wrapper_rel_def_a2557aec54a7a800, true, false);
addRelation("CFGraph.reachable", wrapper_rel_CFGraph_reachable_c344462befee4909, false, false);
addRelation("alias", wrapper_rel_alias_36893f0f24e80d93, false, true);
addRelation("root_vars", wrapper_rel_root_vars_9dd5ee9984886e0d, false, true);
addRelation("aliasUsed", wrapper_rel_aliasUsed_65edfdff09a886e0, false, true);
}

 Sf_stack_roots::~Sf_stack_roots(){
}

void Sf_stack_roots::runFunction(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){

    this->inputDirectory  = std::move(inputDirectoryArg);
    this->outputDirectory = std::move(outputDirectoryArg);
    this->performIO       = performIOArg;
    this->pruneImdtRels   = pruneImdtRelsArg;

    // set default threads (in embedded mode)
    // if this is not set, and omp is used, the default omp setting of number of cores is used.
#if defined(_OPENMP)
    if (0 < getNumThreads()) { omp_set_num_threads(static_cast<int>(getNumThreads())); }
#endif

    signalHandler->set();
// -- query evaluation --
{
 std::vector<RamDomain> args, ret;
stratum_assign_f550d366a9215d2a.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_bind_1968829e9243d389.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_call_587d2d7effb5d130.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_cf_edge_4017fef287699967.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_collect_e5356b85e8033273.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_use_2e20cb5441769259.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_CFGraph_edge_656704795f0096ba.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_def_1d1da3266d2fd4ce.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_CFGraph_reachable_a1359c86b6f7bd73.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_alias_0179d0f4f86c77c2.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_root_vars_19aeb1b6f3a71208.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_aliasUsed_7d447e0118863465.run(args, ret);
}

// -- relation hint statistics --
signalHandler->reset();
}

void Sf_stack_roots::run(){
runFunction("", "", false, false);
}

void Sf_stack_roots::runAll(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){
runFunction(inputDirectoryArg, outputDirectoryArg, performIOArg, pruneImdtRelsArg);
}

void Sf_stack_roots::printAll([[maybe_unused]] std::string outputDirectoryArg){
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","a\tvf\tb\tvg"},{"auxArity","0"},{"name","alias"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 4, \"params\": [\"a\", \"vf\", \"b\", \"vg\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 4, \"types\": [\"r:Location\", \"+:Reference\", \"r:Location\", \"+:Reference\"]}}"}});
if (!outputDirectoryArg.empty()) {directiveMap["output-dir"] = outputDirectoryArg;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_alias_36893f0f24e80d93);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tv"},{"auxArity","0"},{"name","root_vars"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"s:symbol\"]}}"}});
if (!outputDirectoryArg.empty()) {directiveMap["output-dir"] = outputDirectoryArg;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_root_vars_9dd5ee9984886e0d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tv"},{"auxArity","0"},{"name","aliasUsed"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"+:Reference\"]}}"}});
if (!outputDirectoryArg.empty()) {directiveMap["output-dir"] = outputDirectoryArg;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_aliasUsed_65edfdff09a886e0);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

void Sf_stack_roots::loadAll([[maybe_unused]] std::string inputDirectoryArg){
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","caller\tcaller_arg\tcallee\tcallee_arg"},{"auxArity","0"},{"fact-dir","."},{"name","bind"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 4, \"params\": [\"caller\", \"caller_arg\", \"callee\", \"callee_arg\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 4, \"types\": [\"r:Location\", \"+:Reference\", \"s:Function\", \"s:symbol\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_bind_c9210fdc63280a40);
} catch (std::exception& e) {std::cerr << "Error loading bind data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc\tx\ty"},{"auxArity","0"},{"fact-dir","."},{"name","assign"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 3, \"params\": [\"loc\", \"x\", \"y\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 3, \"types\": [\"r:Location\", \"+:Reference\", \"+:Reference\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_assign_e4bb6e0824a16a37);
} catch (std::exception& e) {std::cerr << "Error loading assign data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","caller\tcallee"},{"auxArity","0"},{"fact-dir","."},{"name","call"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"caller\", \"callee\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"r:Location\", \"s:Function\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_call_ee1d8972d66cc25f);
} catch (std::exception& e) {std::cerr << "Error loading call data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\ty"},{"auxArity","0"},{"fact-dir","."},{"name","cf_edge"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"y\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"i:Statement\", \"i:Statement\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_cf_edge_4931a04c8c74bb72);
} catch (std::exception& e) {std::cerr << "Error loading cf_edge data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc"},{"auxArity","0"},{"fact-dir","."},{"name","collect"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 1, \"params\": [\"loc\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 1, \"types\": [\"r:Location\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_collect_092686b367d9983d);
} catch (std::exception& e) {std::cerr << "Error loading collect data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc\tv"},{"auxArity","0"},{"fact-dir","."},{"name","use"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"loc\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"r:Location\", \"+:Reference\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_use_e955e932f22dad4d);
} catch (std::exception& e) {std::cerr << "Error loading use data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","loc\tv"},{"auxArity","0"},{"fact-dir","."},{"name","def"},{"operation","input"},{"params","{\"records\": {\"Location\": {\"arity\": 2, \"params\": [\"func\", \"stmt\"]}}, \"relation\": {\"arity\": 2, \"params\": [\"loc\", \"v\"]}}"},{"types","{\"ADTs\": {\"+:Reference\": {\"arity\": 2, \"branches\": [{\"name\": \"Member\", \"types\": [\"s:symbol\", \"s:symbol\"]}, {\"name\": \"Variable\", \"types\": [\"s:symbol\"]}], \"enum\": false}}, \"records\": {\"r:Location\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}, \"relation\": {\"arity\": 2, \"types\": [\"r:Location\", \"+:Reference\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_def_a2557aec54a7a800);
} catch (std::exception& e) {std::cerr << "Error loading def data: " << e.what() << '\n';
exit(1);
}
}

void Sf_stack_roots::dumpInputs(){
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "bind";
rwOperation["types"] = "{\"relation\": {\"arity\": 4, \"auxArity\": 0, \"types\": [\"r:Location\", \"+:Reference\", \"s:Function\", \"s:symbol\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_bind_c9210fdc63280a40);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "assign";
rwOperation["types"] = "{\"relation\": {\"arity\": 3, \"auxArity\": 0, \"types\": [\"r:Location\", \"+:Reference\", \"+:Reference\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_assign_e4bb6e0824a16a37);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "call";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"r:Location\", \"s:Function\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_call_ee1d8972d66cc25f);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "cf_edge";
rwOperation["types"] = "{\"relation\": {\"arity\": 3, \"auxArity\": 0, \"types\": [\"s:Function\", \"i:Statement\", \"i:Statement\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_cf_edge_4931a04c8c74bb72);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "collect";
rwOperation["types"] = "{\"relation\": {\"arity\": 1, \"auxArity\": 0, \"types\": [\"r:Location\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_collect_092686b367d9983d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "use";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"r:Location\", \"+:Reference\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_use_e955e932f22dad4d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "def";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"r:Location\", \"+:Reference\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_def_a2557aec54a7a800);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

void Sf_stack_roots::dumpOutputs(){
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "alias";
rwOperation["types"] = "{\"relation\": {\"arity\": 4, \"auxArity\": 0, \"types\": [\"r:Location\", \"+:Reference\", \"r:Location\", \"+:Reference\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_alias_36893f0f24e80d93);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "root_vars";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"s:Function\", \"s:symbol\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_root_vars_9dd5ee9984886e0d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "aliasUsed";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"s:Function\", \"+:Reference\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_aliasUsed_65edfdff09a886e0);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

SymbolTable& Sf_stack_roots::getSymbolTable(){
return symTable;
}

RecordTable& Sf_stack_roots::getRecordTable(){
return recordTable;
}

void Sf_stack_roots::setNumThreads(std::size_t numThreadsValue){
SouffleProgram::setNumThreads(numThreadsValue);
symTable.setNumLanes(getNumThreads());
recordTable.setNumLanes(getNumThreads());
regexCache.setNumLanes(getNumThreads());
}

void Sf_stack_roots::executeSubroutine(std::string name,const std::vector<RamDomain>& args,std::vector<RamDomain>& ret){
if (name == "CFGraph.edge") {
stratum_CFGraph_edge_656704795f0096ba.run(args, ret);
return;}
if (name == "CFGraph.reachable") {
stratum_CFGraph_reachable_a1359c86b6f7bd73.run(args, ret);
return;}
if (name == "alias") {
stratum_alias_0179d0f4f86c77c2.run(args, ret);
return;}
if (name == "aliasUsed") {
stratum_aliasUsed_7d447e0118863465.run(args, ret);
return;}
if (name == "assign") {
stratum_assign_f550d366a9215d2a.run(args, ret);
return;}
if (name == "bind") {
stratum_bind_1968829e9243d389.run(args, ret);
return;}
if (name == "call") {
stratum_call_587d2d7effb5d130.run(args, ret);
return;}
if (name == "cf_edge") {
stratum_cf_edge_4017fef287699967.run(args, ret);
return;}
if (name == "collect") {
stratum_collect_e5356b85e8033273.run(args, ret);
return;}
if (name == "def") {
stratum_def_1d1da3266d2fd4ce.run(args, ret);
return;}
if (name == "root_vars") {
stratum_root_vars_19aeb1b6f3a71208.run(args, ret);
return;}
if (name == "use") {
stratum_use_2e20cb5441769259.run(args, ret);
return;}
fatal(("unknown subroutine " + name).c_str());
}

} // namespace  souffle
namespace souffle {
SouffleProgram *newInstance_stack_roots(){return new  souffle::Sf_stack_roots;}
SymbolTable *getST_stack_roots(SouffleProgram *p){return &reinterpret_cast<souffle::Sf_stack_roots*>(p)->getSymbolTable();}
} // namespace souffle

#ifndef __EMBEDDED_SOUFFLE__
#include "souffle/CompiledOptions.h"
int main(int argc, char** argv)
{
try{
souffle::CmdOptions opt(R"(mycpp/stack_roots.dl)",
R"()",
R"()",
false,
R"()",
1);
if (!opt.parse(argc,argv)) return 1;
souffle::Sf_stack_roots obj;
#if defined(_OPENMP) 
obj.setNumThreads(opt.getNumJobs());

#endif
obj.runAll(opt.getInputFileDir(), opt.getOutputFileDir());
return 0;
} catch(std::exception &e) { souffle::SignalHandler::instance()->error(e.what());}
}
#endif

namespace  souffle {
using namespace souffle;
class factory_Sf_stack_roots: souffle::ProgramFactory {
public:
souffle::SouffleProgram* newInstance();
 factory_Sf_stack_roots();
private:
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
souffle::SouffleProgram* factory_Sf_stack_roots::newInstance(){
return new  souffle::Sf_stack_roots();
}

 factory_Sf_stack_roots::factory_Sf_stack_roots():
souffle::ProgramFactory("stack_roots"){
}

} // namespace  souffle
namespace souffle {

#ifdef __EMBEDDED_SOUFFLE__
extern "C" {
souffle::factory_Sf_stack_roots __factory_Sf_stack_roots_instance;
}
#endif
} // namespace souffle

