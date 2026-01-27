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
  * Search the global `index` against `query`.
  *
  * The matching algorithm is as follows, include all items with:
  *  - An exact match
  *  - Damerau-Levenshtein distance <= 5
  *
  * Note that all matching is case-insensitive.
  *
  * Only the top 25 results are given. We first show the exact matches, and then
  * the inexact matches ranked by decreasing DL distance.
  */
async function search(query) {
  if (!query) {
    return [];
  }

  const index = await getIndex();

  // We do case insensitive matching.
  query = query.toLowerCase();

  // Results is a list of pairs [entry, rank] where a lower rank is better.
  const results = [];
  for (const entry of index) {
    const symbol = entry.symbol.toLowerCase();
    if (symbol.includes(query)) {
      results.push([entry, 0]);
      continue;
    }

    const distance = damerauLevenshteinDistance(query, entry.symbol);
    if (distance > 5) {
      continue;
    }

    results.push([entry, distance]);
  }

  results.sort(([_a, aRank], [_b, bRank]) => aRank - bRank);
  return results.map(([entry, _rank]) => entry).slice(0, 25);
}

function searchbar() {
  const searchDiv = document.getElementById("search");

  // Create the searchbar dynamically so that users without JS enabled don't get
  // a broken searchbar
  const searchbar = document.createElement('input');
  searchbar.id = 'searchbar';
  searchbar.setAttribute('placeholder', 'Search');
  searchbar.setAttribute('title', 'Search');
  searchbar.setAttribute('autocapitalize', 'none');
  searchbar.setAttribute('enterkeyhint', 'search');
  searchDiv.appendChild(searchbar);

  // We show a loading bar on the first fetch.
  const loading = document.createElement('p');
  loading.innerText = 'Loading...';
  const showLoading = () => loading.style.display = 'block';
  const hideLoading = () => loading.style.display = 'none';
  hideLoading();
  searchDiv.appendChild(loading);

  let resultsList = null;
  searchbar.addEventListener('input', async (event) => {
    showLoading();
    const query = event.target.value;
    const results = await search(query);
    hideLoading();

    // Clear the previous results, if present
    if (resultsList) {
      resultsList.remove();
    }

    resultsList = document.createElement('ul');
    searchDiv.appendChild(resultsList);

    for (const result of results) {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.innerHTML = result.symbol;
      link.href = window.basePath + '/' + result.anchor;
      item.appendChild(link);
      resultsList.appendChild(item);
    }
  });
}

searchbar();
