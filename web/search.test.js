const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const fs = require('node:fs/promises');
const vm = require('node:vm');

/**
 * Load web/search.js in a context which sets window.test to true.
 *
 * Without this, search.js will try to interact with the DOM and then fail
 * because node.js doesn't provide DOM APIs.
 *
 * Returns the module (an object with all defined functions).
 *
 * Scaffolded with some help from ChatGPT.
 */
async function loadSearchModule() {
  const sandbox = {
    window: { test: true },
  };
  sandbox.globalThis = sandbox;

  const scriptPath = path.join(__dirname, 'search.js');
  const source = await fs.readFile(scriptPath, 'utf8');
  const context = vm.createContext(sandbox);
  new vm.Script(source, { filename: scriptPath }).runInContext(context);
  return context;
}

/**
 * Because we execute in a node.js VM context [0], you cannot assert.deepStrictEqual
 * because array objects inside the vm context are different from those outside
 * the context.
 *
 * If we do a (de)serialize loop through JSON, we reconstruct the objects using
 * the main test context, which can then be compared using assert.deepStrictEqual.
 *
 * Without this, we get "Values have same structure but are not reference-equal"
 * errors when running this test.
 *
 * See the "filterAndRank keeps matching descendants only" test for usage.
 *
 * [0]: https://nodejs.org/api/vm.html#vmcreatecontextcontextobject-options
 */
function pullFromContext(value) {
  return JSON.parse(JSON.stringify(value));
}

let search;
test.before(async () => {
  search = await loadSearchModule();
});

test('damerauLevenshteinDistance handles common edits', () => {
  const cases = [
    // Empty string is fine
    { a: '', b: '', expected: 0 },

    // Exact match
    { a: 'abc', b: 'abc', expected: 0 },

    // 1 Deletion
    { a: 'abc', b: 'ab', expected: 1 },

    // 3 Additions
    { a: '', b: 'abc', expected: 3 },

    // 1 replacement
    { a: 'abc', b: 'adc', expected: 1 },

    // 1 Transposition
    { a: 'ca', b: 'ac', expected: 1 },

    // 2 replacements, 1 addition
    { a: 'kitten', b: 'sitting', expected: 3 },
  ];

  for (const { a, b, expected } of cases) {
    assert.strictEqual(
      search.damerauLevenshteinDistance(a, b),
      expected,
      `distance between "${a}" and "${b}" should be ${expected}`
    );
    assert.strictEqual(
      search.damerauLevenshteinDistance(b, a),
      expected,
      `distance should be symmetric for "${b}" vs "${a}"`
    );
  }
});

test('rankSymbol orders exact and fuzzy matches', () => {
  assert.strictEqual(search.rankSymbol('method', 'method'), 0);
  assert.strictEqual(search.rankSymbol('method', 'methd'), 1);
  assert.strictEqual(search.rankSymbol('method', 'xxxxxxxxxxxx'), Infinity);
});

test('filterAndRank keeps matching descendants only', () => {
  const index = [
    {
      symbol: 'Root',
      anchor: 'root',
      children: [
        { symbol: 'ChildMatch', anchor: 'child-match', children: [] },
        { symbol: 'ChildOther', anchor: 'child-other', children: [] },
      ],
    },
    { symbol: 'Sibling', anchor: 'sibling', children: [] },
  ];

  const pruned = search.filterAndRank(index, 'match');

  assert.deepStrictEqual(pullFromContext(pruned), [
    {
      _rank: 0,
      symbol: 'Root',
      anchor: 'root',
      children: [
        { _rank: 0, symbol: 'ChildMatch', anchor: 'child-match', children: [] },
      ],
    },
  ]);
});

test('trimResults enforces a render limit while keeping parents', () => {
  const results = [
    {
      symbol: 'Root',
      anchor: 'root',
      children: [
        { symbol: 'ChildOne', anchor: 'c1', children: [] },
        { symbol: 'ChildTwo', anchor: 'c2', children: [] },
      ],
    },
    { symbol: 'Sibling', anchor: 'sibling', children: [] },
  ];

  const trimmedThree = search.trimResults(results, 3);
  assert.deepStrictEqual(pullFromContext(trimmedThree), [
    {
      symbol: 'Root',
      anchor: 'root',
      children: [
        { symbol: 'ChildOne', anchor: 'c1', children: [] },
        { symbol: 'ChildTwo', anchor: 'c2', children: [] },
      ],
    },
  ]);

  const trimmedTwo = search.trimResults(results, 2);
  assert.deepStrictEqual(pullFromContext(trimmedTwo), [
    {
      symbol: 'Root',
      anchor: 'root',
      children: [
        { symbol: 'ChildOne', anchor: 'c1', children: [] },
      ],
    },
  ]);
});
