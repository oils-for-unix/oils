// Fetch the search index only when the user wants to search. Then cache it thereafter.
//
// We also have to avoid race conditions. On very slow networks, multiple calls to getIndex can be
// made before the fetch completes. To remedy this, we store the promise returning the index in
// _index. Then any calls to await getIndex() implicitly wait on this single promise.
let _index;
function getIndex() {
  if (!_index) {
    _index = (async () => {
      const res = await fetch(`${window.basePath}/index.json`);
      _index = await res.json();
      return _index;
    })();
  }

  return _index;
}

/**
 * True Damerau–Levenshtein distance (allows multiple transpositions).
 * Adapted from [0] with help from ChatGPT 5.2.
 *
 * Computes the DL distance between textA and textB. This is the number of edits between A and B. The possible edits are:
 * - Insertion (adding a single char)
 * - Deletion (removing a single char)
 * - Substitution (changing a single char)
 * - Transposition (swapping the locations of 2 chars)
 *
 * [0] https://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance#Distance_with_adjacent_transpositions
 */
function damerauLevenshteinDistance(textA, textB) {
  const lenA = textA.length;
  const lenB = textB.length;

  const INF = lenA + lenB;

  // lastRowByChar == da in the pseudocode:
  // maps a character -> last row index (1..lenA) where it appeared in textA
  const lastRowByChar = new Map();

  // dist is the shifted version of d. Size: (lenA+2) x (lenB+2)
  const dist = Array.from({ length: lenA + 2 }, () => new Array(lenB + 2).fill(0));

  // Initialize sentinel borders
  dist[0][0] = INF;
  for (let i = 0; i <= lenA; i++) {
    dist[i + 1][0] = INF; // d[i, -1]
    dist[i + 1][1] = i;   // d[i,  0]
  }
  for (let j = 0; j <= lenB; j++) {
    dist[0][j + 1] = INF; // d[-1, j]
    dist[1][j + 1] = j;   // d[ 0, j]
  }

  // Main dynamic programming algorithm
  for (let i = 1; i <= lenA; i++) {
    let lastMatchingColInB = 0; // db in the pseudocode (last column j where a[i] matched)
    const charA = textA[i - 1];

    for (let j = 1; j <= lenB; j++) {
      const charB = textB[j - 1];

      const lastRowWithCharBInA = lastRowByChar.get(charB) ?? 0; // k := da[b[j]]
      const lastMatchingColForThisRow = lastMatchingColInB;      // ℓ := db

      const cost = (charA === charB) ? 0 : 1;
      if (cost === 0) lastMatchingColInB = j;

      // Shifted accesses:
      // d[i-1, j-1] -> dist[i][j]
      // d[i,   j-1] -> dist[i+1][j]
      // d[i-1, j  ] -> dist[i][j+1]
      const substitution = dist[i][j] + cost;
      const insertion    = dist[i + 1][j] + 1;
      const deletion     = dist[i][j + 1] + 1;

      // Transposition term (shifted):
      // d[k-1, ℓ-1] in pseudocode -> dist[k][ℓ]
      const transposition =
        dist[lastRowWithCharBInA][lastMatchingColForThisRow] +
        (i - lastRowWithCharBInA - 1) +
        cost +
        (j - lastMatchingColForThisRow - 1);

      dist[i + 1][j + 1] = Math.min(substitution, insertion, deletion, transposition);
    }

    // da[a[i]] := i
    lastRowByChar.set(charA, i);
  }

  // return d[lenA, lenB] -> dist[lenA+1][lenB+1]
  return dist[lenA + 1][lenB + 1];
}

/**
 * Compute a match rank for a single label against query.
 * Lower is better. 0 = exact substring match, 1..5 = fuzzy, Infinity = no match.
 *
 * Expects both symbol and query to be all lowercase.
 */
function rankSymbol(symbol, query) {
  // Exact match
  if (symbol.includes(query)) return 0;

  const d = damerauLevenshteinDistance(query, symbol);
  return d <= 5 ? d : Infinity;
}

/**
 * Recursively filter the index to only branches containing matches.
 *
 * `query` must be a lowercase string.
 */
function filterAndRank(index, query) {
  const kept = [];
  for (const node of index) {
    const symbol = node.symbol.toLowerCase();
    const anchor = node.anchor;
    const children = node.children ?? []; // We omit the children in the index when empty

    const selfRank = rankSymbol(symbol, query);
    const keptChildren = filterAndRank(children, query);

    // Best descendant rank (if any)
    let bestChildRank = Infinity;
    for (const c of keptChildren) {
      if (c._rank < bestChildRank) bestChildRank = c._rank;
    }

    // Keep node if it matches or has matching descendants
    const bestRank = Math.min(selfRank, bestChildRank);
    if (bestRank !== Infinity) {
      const copy = { _rank: bestRank, symbol: node.symbol, anchor, children: keptChildren };
      kept.push(copy);
    }
  }

  kept.sort((a, b) => (a._rank ?? Infinity) - (b._rank ?? Infinity));
  return kept;
}

/**
 * Trim the pruned tree to at most `limit` total rendered links (nodes).
 * Keeps structure (parents) only as needed to show kept children.
 *
 * This way searching 'a' doesn't fill the entire page with junk.
 * TODO: pagination / a next button
 */
function trimResults(results, limit) {
  let count = 0;

  function walk(list) {
    const out = [];
    for (const node of list) {
      if (count >= limit) break;

      // Count this node as one rendered link
      count += 1;

      const trimmedChildren = walk(node.children);

      out.push({
        symbol: node.symbol,
        anchor: node.anchor,
        children: trimmedChildren,
      });
    }
    return out;
  }

  return walk(results);
}

/**
 * Search across the website using the global search index.
 * Returns a pruned tree (array of nodes) ready to render (see renderResults).
 *
 * Matching algorithm:
 *  - Exact substring match: rank 0
 *  - DL distance <= 5: rank 1..5
 *  - Otherwise excluded
 *
 * Only the top `limit` rendered nodes are returned (default 25).
 */
async function search(query) {
  if (!query) return [];

  const index = await getIndex();
  const pruned = filterAndRank(index, query.toLowerCase());
  return trimResults(pruned, /* limit */ 25);
}

/**
 * Render as nested <ul>/<li> where *every* item is a link.
 */
function renderResults(nodes) {
  const ul = document.createElement("ul");

  for (const node of nodes) {
    const li = document.createElement("li");

    const a = document.createElement("a");
    a.textContent = String(node.symbol ?? "");
    a.href = (typeof node.anchor === "string")
      ? window.basePath + "/" + node.anchor
      : "#";
    li.appendChild(a);

    const children = Array.isArray(node.children) ? node.children : [];
    if (children.length) {
      li.appendChild(renderResults(children));
    }

    ul.appendChild(li);
  }

  return ul;
}

function searchbar() {
  const searchDiv = document.getElementById("search");

  // Create the searchbar dynamically so that users without JS enabled don't get
  // a broken searchbar
  const searchbar = document.createElement("input");
  searchbar.id = "searchbar";
  searchbar.setAttribute("placeholder", "Search");
  searchbar.setAttribute("title", "Search");
  searchbar.setAttribute("autocapitalize", "none");
  searchbar.setAttribute("enterkeyhint", "search");
  searchDiv.appendChild(searchbar);

  // We show a loading bar on the first fetch.
  const loading = document.createElement("p");
  loading.innerText = "Loading...";
  const showLoading = () => (loading.style.display = "block");
  const hideLoading = () => (loading.style.display = "none");
  hideLoading();
  searchDiv.appendChild(loading);

  let resultsList = null;
  searchbar.addEventListener("input", async (event) => {
    showLoading();
    const query = event.target.value;

    const prunedTree = await search(query);

    hideLoading();

    // We have to clear the previous results, if present
    if (resultsList) {
      resultsList.remove();
    }

    resultsList = renderResults(prunedTree);
    searchDiv.appendChild(resultsList);
  });
}

if (!window.test) {
  // Only run the UI in a non-test environment
  searchbar();
}
