#define SOUFFLE_GENERATOR_VERSION "UNKNOWN"
#include "souffle/CompiledSouffle.h"
#include "souffle/SignalHandler.h"
#include "souffle/SouffleInterface.h"
#include "souffle/datastructure/BTree.h"
#include "souffle/io/IOSystem.h"
#include <any>
namespace functors {
extern "C" {
}
} //namespace functors
namespace souffle::t_btree_iii__2_0_1__001__111 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 3;
using t_tuple = Tuple<RamDomain, 3>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]));
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
range<t_ind_0::iterator> lowerUpperRange_001(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_001(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_iii__2_0_1__001__111 
namespace souffle::t_btree_iii__2_0_1__001__111 {
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
range<t_ind_0::iterator> Type::lowerUpperRange_001(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_001(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_001(lower,upper,h);
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
o << " arity 3 direct b-tree index 0 lex-order [2,0,1]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_iii__2_0_1__001__111 
namespace souffle::t_btree_ii__0_1__11 {
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
} // namespace souffle::t_btree_ii__0_1__11 
namespace souffle::t_btree_ii__0_1__11 {
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
} // namespace souffle::t_btree_ii__0_1__11 
namespace souffle::t_btree_ii__0_1__11__10 {
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
range<t_ind_0::iterator> lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_ii__0_1__11__10 
namespace souffle::t_btree_ii__0_1__11__10 {
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
range<t_ind_0::iterator> Type::lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_10(lower,upper,h);
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
} // namespace souffle::t_btree_ii__0_1__11__10 
namespace  souffle {
using namespace souffle;
class Stratum_call_104fac07831e2229 {
public:
 Stratum_call_104fac07831e2229(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_iii__2_0_1__001__111::Type& rel_call_ee1d8972d66cc25f);
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
t_btree_iii__2_0_1__001__111::Type* rel_call_ee1d8972d66cc25f;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_call_104fac07831e2229::Stratum_call_104fac07831e2229(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_iii__2_0_1__001__111::Type& rel_call_ee1d8972d66cc25f):
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
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","caller\ts\tcallee"},{"auxArity","0"},{"fact-dir","."},{"name","call"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"caller\", \"s\", \"callee\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"i:Statement\", \"s:Function\"]}}"}});
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
class Stratum_might_collect_beadc513d07ff032 {
public:
 Stratum_might_collect_beadc513d07ff032(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_ii__0_1__11__10::Type& rel_delta_might_collect_d651f71586aafe59,t_btree_ii__0_1__11__10::Type& rel_new_might_collect_5d48ef45a97e4618,t_btree_iii__2_0_1__001__111::Type& rel_call_ee1d8972d66cc25f,t_btree_ii__0_1__11::Type& rel_might_collect_ef1d0b06d36e4ddc);
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
t_btree_ii__0_1__11__10::Type* rel_delta_might_collect_d651f71586aafe59;
t_btree_ii__0_1__11__10::Type* rel_new_might_collect_5d48ef45a97e4618;
t_btree_iii__2_0_1__001__111::Type* rel_call_ee1d8972d66cc25f;
t_btree_ii__0_1__11::Type* rel_might_collect_ef1d0b06d36e4ddc;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_might_collect_beadc513d07ff032::Stratum_might_collect_beadc513d07ff032(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_ii__0_1__11__10::Type& rel_delta_might_collect_d651f71586aafe59,t_btree_ii__0_1__11__10::Type& rel_new_might_collect_5d48ef45a97e4618,t_btree_iii__2_0_1__001__111::Type& rel_call_ee1d8972d66cc25f,t_btree_ii__0_1__11::Type& rel_might_collect_ef1d0b06d36e4ddc):
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
rel_delta_might_collect_d651f71586aafe59(&rel_delta_might_collect_d651f71586aafe59),
rel_new_might_collect_5d48ef45a97e4618(&rel_new_might_collect_5d48ef45a97e4618),
rel_call_ee1d8972d66cc25f(&rel_call_ee1d8972d66cc25f),
rel_might_collect_ef1d0b06d36e4ddc(&rel_might_collect_ef1d0b06d36e4ddc){
}

void Stratum_might_collect_beadc513d07ff032::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(might_collect(f,s) :- 
   call(f,s,"mylib.MaybeCollect").
in file call-graph.dl [14:1-14:57])_");
if(!(rel_call_ee1d8972d66cc25f->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_call_ee1d8972d66cc25f_op_ctxt,rel_call_ee1d8972d66cc25f->createContext());
CREATE_OP_CONTEXT(rel_might_collect_ef1d0b06d36e4ddc_op_ctxt,rel_might_collect_ef1d0b06d36e4ddc->createContext());
auto range = rel_call_ee1d8972d66cc25f->lowerUpperRange_001(Tuple<RamDomain,3>{{ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(RamSigned(0))}},Tuple<RamDomain,3>{{ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(RamSigned(0))}},READ_OP_CONTEXT(rel_call_ee1d8972d66cc25f_op_ctxt));
for(const auto& env0 : range) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_might_collect_ef1d0b06d36e4ddc->insert(tuple,READ_OP_CONTEXT(rel_might_collect_ef1d0b06d36e4ddc_op_ctxt));
}
}
();}
[&](){
CREATE_OP_CONTEXT(rel_delta_might_collect_d651f71586aafe59_op_ctxt,rel_delta_might_collect_d651f71586aafe59->createContext());
CREATE_OP_CONTEXT(rel_might_collect_ef1d0b06d36e4ddc_op_ctxt,rel_might_collect_ef1d0b06d36e4ddc->createContext());
for(const auto& env0 : *rel_might_collect_ef1d0b06d36e4ddc) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_delta_might_collect_d651f71586aafe59->insert(tuple,READ_OP_CONTEXT(rel_delta_might_collect_d651f71586aafe59_op_ctxt));
}
}
();auto loop_counter = RamUnsigned(1);
iter = 0;
for(;;) {
signalHandler->setMsg(R"_(might_collect(f,s) :- 
   call(f,s,g),
   might_collect(g,_).
in file call-graph.dl [15:1-15:59])_");
if(!(rel_call_ee1d8972d66cc25f->empty()) && !(rel_delta_might_collect_d651f71586aafe59->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_might_collect_d651f71586aafe59_op_ctxt,rel_delta_might_collect_d651f71586aafe59->createContext());
CREATE_OP_CONTEXT(rel_new_might_collect_5d48ef45a97e4618_op_ctxt,rel_new_might_collect_5d48ef45a97e4618->createContext());
CREATE_OP_CONTEXT(rel_call_ee1d8972d66cc25f_op_ctxt,rel_call_ee1d8972d66cc25f->createContext());
CREATE_OP_CONTEXT(rel_might_collect_ef1d0b06d36e4ddc_op_ctxt,rel_might_collect_ef1d0b06d36e4ddc->createContext());
for(const auto& env0 : *rel_call_ee1d8972d66cc25f) {
if( !rel_delta_might_collect_d651f71586aafe59->lowerUpperRange_10(Tuple<RamDomain,2>{{ramBitCast(env0[2]), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,2>{{ramBitCast(env0[2]), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_delta_might_collect_d651f71586aafe59_op_ctxt)).empty() && !(rel_might_collect_ef1d0b06d36e4ddc->contains(Tuple<RamDomain,2>{{ramBitCast(env0[0]),ramBitCast(env0[1])}},READ_OP_CONTEXT(rel_might_collect_ef1d0b06d36e4ddc_op_ctxt)))) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_new_might_collect_5d48ef45a97e4618->insert(tuple,READ_OP_CONTEXT(rel_new_might_collect_5d48ef45a97e4618_op_ctxt));
}
}
}
();}
if(rel_new_might_collect_5d48ef45a97e4618->empty()) break;
[&](){
CREATE_OP_CONTEXT(rel_new_might_collect_5d48ef45a97e4618_op_ctxt,rel_new_might_collect_5d48ef45a97e4618->createContext());
CREATE_OP_CONTEXT(rel_might_collect_ef1d0b06d36e4ddc_op_ctxt,rel_might_collect_ef1d0b06d36e4ddc->createContext());
for(const auto& env0 : *rel_new_might_collect_5d48ef45a97e4618) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_might_collect_ef1d0b06d36e4ddc->insert(tuple,READ_OP_CONTEXT(rel_might_collect_ef1d0b06d36e4ddc_op_ctxt));
}
}
();std::swap(rel_delta_might_collect_d651f71586aafe59, rel_new_might_collect_5d48ef45a97e4618);
rel_new_might_collect_5d48ef45a97e4618->purge();
loop_counter = (ramBitCast<RamUnsigned>(loop_counter) + ramBitCast<RamUnsigned>(RamUnsigned(1)));
iter++;
}
iter = 0;
rel_delta_might_collect_d651f71586aafe59->purge();
rel_new_might_collect_5d48ef45a97e4618->purge();
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\ts"},{"auxArity","0"},{"name","might_collect"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"s\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}"}});
if (outputDirectory == "-"){directiveMap["IO"] = "stdout"; directiveMap["headers"] = "true";}
else if (!outputDirectory.empty()) {directiveMap["output-dir"] = outputDirectory;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_might_collect_ef1d0b06d36e4ddc);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}
if (pruneImdtRels) rel_call_ee1d8972d66cc25f->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Sf__: public SouffleProgram {
public:
 Sf__();
 ~Sf__();
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
SpecializedRecordTable<0> recordTable;
ConcurrentCache<std::string,std::regex> regexCache;
Own<t_btree_iii__2_0_1__001__111::Type> rel_call_ee1d8972d66cc25f;
souffle::RelationWrapper<t_btree_iii__2_0_1__001__111::Type> wrapper_rel_call_ee1d8972d66cc25f;
Own<t_btree_ii__0_1__11::Type> rel_might_collect_ef1d0b06d36e4ddc;
souffle::RelationWrapper<t_btree_ii__0_1__11::Type> wrapper_rel_might_collect_ef1d0b06d36e4ddc;
Own<t_btree_ii__0_1__11__10::Type> rel_delta_might_collect_d651f71586aafe59;
Own<t_btree_ii__0_1__11__10::Type> rel_new_might_collect_5d48ef45a97e4618;
Stratum_call_104fac07831e2229 stratum_call_587d2d7effb5d130;
Stratum_might_collect_beadc513d07ff032 stratum_might_collect_cc50af26f53a71ac;
std::string inputDirectory;
std::string outputDirectory;
SignalHandler* signalHandler{SignalHandler::instance()};
std::atomic<RamDomain> ctr{};
std::atomic<std::size_t> iter{};
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Sf__::Sf__():
symTable({
	R"_(mylib.MaybeCollect)_",
}),
recordTable(),
regexCache(),
rel_call_ee1d8972d66cc25f(mk<t_btree_iii__2_0_1__001__111::Type>()),
wrapper_rel_call_ee1d8972d66cc25f(0, *rel_call_ee1d8972d66cc25f, *this, "call", std::array<const char *,3>{{"s:Function","i:Statement","s:Function"}}, std::array<const char *,3>{{"caller","s","callee"}}, 0),
rel_might_collect_ef1d0b06d36e4ddc(mk<t_btree_ii__0_1__11::Type>()),
wrapper_rel_might_collect_ef1d0b06d36e4ddc(1, *rel_might_collect_ef1d0b06d36e4ddc, *this, "might_collect", std::array<const char *,2>{{"s:Function","i:Statement"}}, std::array<const char *,2>{{"f","s"}}, 0),
rel_delta_might_collect_d651f71586aafe59(mk<t_btree_ii__0_1__11__10::Type>()),
rel_new_might_collect_5d48ef45a97e4618(mk<t_btree_ii__0_1__11__10::Type>()),
stratum_call_587d2d7effb5d130(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_call_ee1d8972d66cc25f),
stratum_might_collect_cc50af26f53a71ac(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_delta_might_collect_d651f71586aafe59,*rel_new_might_collect_5d48ef45a97e4618,*rel_call_ee1d8972d66cc25f,*rel_might_collect_ef1d0b06d36e4ddc){
addRelation("call", wrapper_rel_call_ee1d8972d66cc25f, true, false);
addRelation("might_collect", wrapper_rel_might_collect_ef1d0b06d36e4ddc, false, true);
}

 Sf__::~Sf__(){
}

void Sf__::runFunction(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){

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
stratum_call_587d2d7effb5d130.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_might_collect_cc50af26f53a71ac.run(args, ret);
}

// -- relation hint statistics --
signalHandler->reset();
}

void Sf__::run(){
runFunction("", "", false, false);
}

void Sf__::runAll(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){
runFunction(inputDirectoryArg, outputDirectoryArg, performIOArg, pruneImdtRelsArg);
}

void Sf__::printAll([[maybe_unused]] std::string outputDirectoryArg){
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\ts"},{"auxArity","0"},{"name","might_collect"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"s\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"i:Statement\"]}}"}});
if (!outputDirectoryArg.empty()) {directiveMap["output-dir"] = outputDirectoryArg;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_might_collect_ef1d0b06d36e4ddc);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

void Sf__::loadAll([[maybe_unused]] std::string inputDirectoryArg){
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","caller\ts\tcallee"},{"auxArity","0"},{"fact-dir","."},{"name","call"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"caller\", \"s\", \"callee\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"i:Statement\", \"s:Function\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_call_ee1d8972d66cc25f);
} catch (std::exception& e) {std::cerr << "Error loading call data: " << e.what() << '\n';
exit(1);
}
}

void Sf__::dumpInputs(){
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "call";
rwOperation["types"] = "{\"relation\": {\"arity\": 3, \"auxArity\": 0, \"types\": [\"s:Function\", \"i:Statement\", \"s:Function\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_call_ee1d8972d66cc25f);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

void Sf__::dumpOutputs(){
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "might_collect";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"s:Function\", \"i:Statement\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_might_collect_ef1d0b06d36e4ddc);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

SymbolTable& Sf__::getSymbolTable(){
return symTable;
}

RecordTable& Sf__::getRecordTable(){
return recordTable;
}

void Sf__::setNumThreads(std::size_t numThreadsValue){
SouffleProgram::setNumThreads(numThreadsValue);
symTable.setNumLanes(getNumThreads());
recordTable.setNumLanes(getNumThreads());
regexCache.setNumLanes(getNumThreads());
}

void Sf__::executeSubroutine(std::string name,const std::vector<RamDomain>& args,std::vector<RamDomain>& ret){
if (name == "call") {
stratum_call_587d2d7effb5d130.run(args, ret);
return;}
if (name == "might_collect") {
stratum_might_collect_cc50af26f53a71ac.run(args, ret);
return;}
fatal(("unknown subroutine " + name).c_str());
}

} // namespace  souffle
namespace souffle {
SouffleProgram *newInstance__(){return new  souffle::Sf__;}
SymbolTable *getST__(SouffleProgram *p){return &reinterpret_cast<souffle::Sf__*>(p)->getSymbolTable();}
} // namespace souffle

#ifndef __EMBEDDED_SOUFFLE__
#include "souffle/CompiledOptions.h"
int main(int argc, char** argv)
{
try{
souffle::CmdOptions opt(R"(mycpp/datalog/call-graph.dl)",
R"()",
R"()",
false,
R"()",
1);
if (!opt.parse(argc,argv)) return 1;
souffle::Sf__ obj;
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
class factory_Sf__: souffle::ProgramFactory {
public:
souffle::SouffleProgram* newInstance();
 factory_Sf__();
private:
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
souffle::SouffleProgram* factory_Sf__::newInstance(){
return new  souffle::Sf__();
}

 factory_Sf__::factory_Sf__():
souffle::ProgramFactory("_"){
}

} // namespace  souffle
namespace souffle {

#ifdef __EMBEDDED_SOUFFLE__
extern "C" {
souffle::factory_Sf__ __factory_Sf___instance;
}
#endif
} // namespace souffle

