// Copyright 2014 Google Inc. All rights reserved.
// 
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// 
//     http://www.apache.org/licenses/LICENSE-2.0
// 
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//
// Sortable HTML table
// -------------------
// 
// DEPS: ajax.js for appendMessage, etc.
//
// Usage:
//
//   Each page should have gTableStates and gUrlHash variables.  This library
//   only provides functions / classes, not instances.
//
//   Then use these public functions on those variables.  They should be hooked
//   up to initialization and onhashchange events.
//
//   - makeTablesSortable
//   - updateTables
//
// Life of a click
//
// - query existing TableState object to find the new state
// - mutate urlHash
// - location.hash = urlHash.encode()
// - onhashchange
// - decode location.hash into urlHash
// - update DOM
//
// HTML generation requirements:
// - <table id="foo">
// - need <colgroup> for types.
// - For numbers, class="num-cell" as well as <col type="number">
// - single <thead> and <tbody>

'use strict';

function userError(errElem, msg) {
  if (errElem) {
    appendMessage(errElem, msg);
  } else {
    console.log(msg);
  }
}

//
// Key functions for column ordering
//
// TODO: better naming convention?

function identity(x) {
  return x;
}

function lowerCase(x) {
  return x.toLowerCase();
}

// Parse as number.
function asNumber(x) {
  var stripped = x.replace(/[ \t\r\n]/g, '');  
  if (stripped === 'NA') {
    // return lowest value, so NA sorts below everything else.
    return -Number.MAX_VALUE;
  }
  var numClean = x.replace(/[$,]/g, '');  // remove dollar signs and commas
  return parseFloat(numClean);
}

// as a date.
//
// TODO: Parse into JS date object?
// http://stackoverflow.com/questions/19430561/how-to-sort-a-javascript-array-of-objects-by-date
// Uses getTime().  Hm.

function asDate(x) {
  return x;
}

//
// Table Implementation
//

// Given a column array and a key function, construct a permutation of the
// indices [0, n).
function makePermutation(colArray, keyFunc) {
  var pairs = [];  // (index, result of keyFunc on cell)

  var n = colArray.length;
  for (var i = 0; i < n; ++i) {
    var value = colArray[i];

    // NOTE: This could be a URL, so you need to extract that?
    // If it's a URL, take the anchor text I guess.
    var key = keyFunc(value);

    pairs.push([key, i]);
  }

  // Sort by computed key
  pairs.sort(function(a, b) { 
    if (a[0] < b[0]) {
      return -1;
    } else if (a[0] > b[0]) {
      return 1;
    } else {
      return 0;
    }
  });

  // Extract the permutation as second column
  var perm = [];
  for (var i = 0; i < pairs.length; ++i) {
    perm.push(pairs[i][1]);  // append index
  }
  return perm;
}

function extractCol(rows, colIndex) {
  var colArray = [];
  for (var i = 0; i < rows.length; ++i) {
    var row = rows[i];
    colArray.push(row.cells[colIndex].textContent);
  }
  return colArray;
}

// Given an array of DOM row objects, and a list of sort functions (one per
// column), return a list of permutations.
//
// Right now this is eager.  Could be lazy later.
function makeAllPermutations(rows, keyFuncs) {
  var numCols = keyFuncs.length;
  var permutations = [];
  for (var i = 0; i < numCols; ++i) {
    var colArray = extractCol(rows, i);
    var keyFunc = keyFuncs[i];
    var p = makePermutation(colArray, keyFunc);
    permutations.push(p);
  }
  return permutations;
}

// Model object for a table.  (Mostly) independent of the DOM.
function TableState(table, keyFuncs) {
  this.table = table;
  keyFuncs = keyFuncs || [];  // array of column

  // these are mutated
  this.sortCol = -1;  // not sorted by any col
  this.ascending = false;  // if sortCol is sorted in ascending order

  if (table === null) {  // hack so we can pass dummy table
    console.log('TESTING');
    return;
  }

  var bodyRows = table.tBodies[0].rows;
  this.orig = [];  // pointers to row objects in their original order
  for (var i = 0; i < bodyRows.length; ++i) { 
    this.orig.push(bodyRows[i]);
  }

  this.colElems = [];
  var colgroup = table.getElementsByTagName('colgroup')[0];

  // copy it into an array
  if (!colgroup) {
    throw new Error('<colgroup> is required');
  }

  for (var i = 0; i < colgroup.children.length; ++i) {
    var colElem = colgroup.children[i];
    var colType = colElem.getAttribute('type');
    var keyFunc;
    switch (colType) {
      case 'case-sensitive':
        keyFunc = identity;
        break;
      case 'case-insensitive':
        keyFunc = lowerCase;
        break;
      case 'number':
        keyFunc = asNumber;
        break;
      case 'date':
        keyFunc = asDate;
        break;
      default:
        throw new Error('Invalid column type ' + colType);
    }
    keyFuncs[i] = keyFunc;

    this.colElems.push(colElem);
  }

  this.permutations = makeAllPermutations(this.orig, keyFuncs);
}

// Reset sort state.
TableState.prototype.resetSort = function() {
  this.sortCol = -1;  // not sorted by any col
  this.ascending = false;  // if sortCol is sorted in ascending order
};

// Change state for a click on a column.
TableState.prototype.doClick = function(colIndex) {
  if (this.sortCol === colIndex) { // same column; invert direction
    this.ascending = !this.ascending;
  } else {  // different column
    this.sortCol = colIndex;
    // first click makes it *descending*.  Typically you want to see the
    // largest values first.
    this.ascending = false;
  }
};

TableState.prototype.decode = function(stateStr, errElem) {
  var sortCol = parseInt(stateStr);  // parse leading integer
  var lastChar = stateStr[stateStr.length - 1];

  var ascending;
  if (lastChar === 'a') {
    ascending = true;
  } else if (lastChar === 'd') {
    ascending = false;
  } else {
    // The user could have entered a bad ID
    userError(errElem, 'Invalid state string ' + stateStr);
    return;
  }

  this.sortCol = sortCol;
  this.ascending = ascending;
}


TableState.prototype.encode = function() {
  if (this.sortCol === -1) {
    return '';  // default state isn't serialized
  }

  var s = this.sortCol.toString();
  s += this.ascending ? 'a' : 'd';
  return s;
};

// Update the DOM with using this object's internal state.
TableState.prototype.updateDom = function() {
  var tHead = this.table.tHead;
  setArrows(tHead, this.sortCol, this.ascending);

  // Highlight the column that the table is sorted by.
  for (var i = 0; i < this.colElems.length; ++i) {
    // set or clear it.  NOTE: This means we can't have other classes on the
    // <col> tags, which is OK.
    var className = (i === this.sortCol) ? 'highlight' : '';
    this.colElems[i].className = className;
  }

  var n = this.orig.length;
  var tbody = this.table.tBodies[0];

  if (this.sortCol === -1) {  // reset it and return
    for (var i = 0; i < n; ++i) {
      tbody.appendChild(this.orig[i]);
    }
    return;
  }

  var perm = this.permutations[this.sortCol];
  if (this.ascending) {
    for (var i = 0; i < n; ++i) {
      var index = perm[i];
      tbody.appendChild(this.orig[index]);
    }
  } else {  // descending, apply the permutation in reverse order
    for (var i = n - 1; i >= 0; --i) {
      var index = perm[i];
      tbody.appendChild(this.orig[index]);
    }
  }
};

var kTablePrefix = 't:';
var kTablePrefixLength = 2;

// Given a UrlHash instance and a list of tables, mutate tableStates.
function decodeState(urlHash, tableStates, errElem) {
  var keys = urlHash.getKeysWithPrefix(kTablePrefix);  // by convention, t:foo=1a
  for (var i = 0; i < keys.length; ++i) {
    var key = keys[i];
    var tableId = key.substring(kTablePrefixLength);

    if (!tableStates.hasOwnProperty(tableId)) {
      // The user could have entered a bad ID
      userError(errElem, 'Invalid table ID [' + tableId + ']');
      return;
    }

    var state = tableStates[tableId];
    var stateStr = urlHash.get(key);  // e.g. '1d'

    state.decode(stateStr, errElem);
  }
}

// Add <span> element for sort arrows.
function addArrowSpans(tHead) {
  var tHeadCells = tHead.rows[0].cells;
  for (var i = 0; i < tHeadCells.length; ++i) {
    var colHead = tHeadCells[i];
    // Put a space in so the width is relatively constant
    colHead.innerHTML += ' <span class="sortArrow">&nbsp;</span>';
  }
}

// Go through all the cells in the header.  Clear the arrow if there is one.
// Set the one on the correct column.
//
// How to do this?  Each column needs a <span></span> modify the text?
function setArrows(tHead, sortCol, ascending) {
  var tHeadCells = tHead.rows[0].cells;

  for (var i = 0; i < tHeadCells.length; ++i) {
    var colHead = tHeadCells[i];
    var span = colHead.getElementsByTagName('span')[0];

    if (i === sortCol) {
      span.innerHTML = ascending ? '&#x25B4;' : '&#x25BE;';
    } else {
      span.innerHTML = '&nbsp;';  // clear it
    }
  }
}

// Given the URL hash, table states, tableId, and  column index that was
// clicked, visit a new location.
function makeClickHandler(urlHash, tableStates, id, colIndex) {
  return function() {  // no args for onclick=
    var clickedState = tableStates[id];

    clickedState.doClick(colIndex);

    // now urlHash has non-table state, and tableStates is the table state.
    for (var tableId in tableStates) {
      var state = tableStates[tableId];

      var stateStr = state.encode();
      var key = kTablePrefix + tableId;

      if (stateStr === '') {
        urlHash.del(key);
      } else {
        urlHash.set(key, stateStr);
      }
    }

    // move to new location
    location.hash = urlHash.encode();
  };
}

// Go through cells and register onClick
function registerClick(table, urlHash, tableStates) {
  var id = table.id;  // id is required

  var tHeadCells = table.tHead.rows[0].cells;
  for (var colIndex = 0; colIndex < tHeadCells.length; ++colIndex) {
    var colHead = tHeadCells[colIndex];
    // NOTE: in ES5, could use 'bind'.
    colHead.onclick = makeClickHandler(urlHash, tableStates, id, colIndex);
  }
}

//
// Public Functions (TODO: Make a module?)
//

// Parse the URL fragment, and update all tables.  Errors are printed to a DOM
// element.
function updateTables(urlHash, tableStates, statusElem) {
  // State should come from the hash alone, so reset old state.  (We want to
  // keep the permutations though.)
  for (var tableId in tableStates) {
    tableStates[tableId].resetSort();
  }

  decodeState(urlHash, tableStates, statusElem);

  for (var name in tableStates) {
    var state = tableStates[name];
    state.updateDom();
  }
}

// Takes a {tableId: spec} object.  The spec should be an array of sortable
// items.  
// Returns a dictionary of table states.
function makeTablesSortable(urlHash, tables, tableStates) {
  for (var i = 0; i < tables.length; ++i) {
    var table = tables[i];
    var tableId = table.id;

    registerClick(table, urlHash, tableStates);
    tableStates[tableId] = new TableState(table);

    addArrowSpans(table.tHead);
  }
  return tableStates;
}

// table-sort.js can use t:holidays=1d
//
// metric.html can use:
//
// metric=Foo.bar
//
// day.html could use
//
// jobId=X&metric=Foo.bar&day=2015-06-01

