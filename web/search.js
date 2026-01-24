const res = await fetch("/index.json");
const index = await res.json();

function search(query) {
  if (!query) {
    return [];
  }

  const results = [];
  for (const entry of index) {
    if (entry.symbol.includes(query)) {
      results.push(entry);
    }
  }
  return results;
}

const searchDiv = document.getElementById("search");
const searchbar = document.getElementById("searchbar");

let resultsList = null;
searchbar.addEventListener('input', async (event) => {
  const query = event.target.value;
  const results = search(query);

  if (resultsList) {
    resultsList.remove();
  }

  resultsList = document.createElement('ul');
  searchDiv.appendChild(resultsList);

  for (const result of results) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.innerHTML = result.symbol;
    link.href = '/' + result.anchor;
    item.appendChild(link);
    resultsList.appendChild(item);
  }
});
