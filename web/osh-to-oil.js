// For osh-to-oil.html.

'use strict';

// Append a message to an element.  Used for errors.
function appendMessage(elem, msg) {
  elem.innerHTML += msg + '<br />';
}

// jQuery-like AJAX helper, but simpler.

// Requires an element with id "status" to show errors.
//
// Args:
//   errElem: optional element to append error messages to.  If null, then
//     alert() on error.
//   success: callback that is passed the xhr object.
function ajaxGet(url, errElem, success) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', url, true /*async*/);
  xhr.onreadystatechange = function() {
    if (xhr.readyState != 4 /*DONE*/) {
      return;
    }

    if (xhr.status != 200) {
      var msg = 'ERROR requesting ' + url + ': ' + xhr.status + ' ' +
                xhr.statusText;
      if (errElem) {
        appendMessage(errElem, msg);
      } else {
        alert(msg);
      }
      return;
    }

    success(xhr);
  };
  xhr.send();
}

// Fill in title and iframe src attributes.
function loadSource(sourceName, statusElem) {
  var sourceElem = document.getElementById('sourceFrames');

  document.getElementById('title').innerHTML = sourceName;

  document.getElementById('orig').src = sourceName + '.txt';
  document.getElementById('oil').src = sourceName + '.oil';
  document.getElementById('ast').src = sourceName + '-AST.html';
  appendMessage(statusElem, "Loaded contents for " + sourceName);
}

function getNameFromHash(urlHash, statusElem) {
  var h = urlHash.substring(1);  // without leading #
  if (h.length < 1) {
    appendMessage(statusElem, "Invalid URL hash: [" + urlHash + "]");
    return null;
  }
  return h;
}

function onLoad(urlHash, globals, statusElem) {
  onHashChange(urlHash, globals, statusElem);
}

// This is the onhashchange handler.
function onHashChange(urlHash, globals, statusElem) {
  var sourceName = getNameFromHash(urlHash, statusElem);
  if (sourceName === null) return;

  loadSource(sourceName, statusElem)
}
