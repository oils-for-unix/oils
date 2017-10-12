// Minimal AJAX library.
//
// The motivation is that we want to generate PNG, JSON, CSV, etc. from R.
// And maybe some HTML fragments.  But we don't want to generate a different
// skeleton for every page.  It's nice just to hit F5 and see the changes
// reloaded.  It's like "PHP in the browser'.

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

function jsonGet(url, errElem, success) {
  ajaxGet(url, errElem, function(xhr) {
    try {
      var j = JSON.parse(xhr.responseText);
    } catch (e) {
      appendMessage(errElem, `Parsing JSON in ${url} failed`);
    }
    success(j);
  });
}

function htmlEscape(unsafe) {
  return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

//
// UrlHash
//

// helper
function _decode(s) {
  var obj = {};
  var parts = s.split('&');
  for (var i = 0; i < parts.length; ++i) {
    if (parts[i].length === 0) {
      continue;  // quirk: ''.split('&') is [''] ?  Should be a 0-length array.
    }
    var pair = parts[i].split('=');
    obj[pair[0]] = pair[1];  // for now, assuming no =
  }
  return obj;
}

function _encode(d) {
  var parts = [];
  for (var name in d) {
    var s = name;
    s += '=';
    var value = d[name];
    s += encodeURIComponent(value);
    parts.push(s);
  }
  return parts.join('&');
}


// UrlHash Constructor.
// Args:
//   hashStr: location.hash
function UrlHash(hashStr) {
  this.reset(hashStr);
}

UrlHash.prototype.reset = function(hashStr) {
  var h = hashStr.substring(1);  // without leading #
  // Internal storage is string -> string
  this.dict = _decode(h);
}

UrlHash.prototype.set = function(name, value) {
  this.dict[name] = value;
};

UrlHash.prototype.del = function(name) {
  delete this.dict[name];
};

UrlHash.prototype.get = function(name ) {
  return this.dict[name];
};

// e.g. Table states have keys which start with 't:'.
UrlHash.prototype.getKeysWithPrefix = function(prefix) {
  var keys = [];
  for (var name in this.dict) {
    if (name.indexOf(prefix) === 0) {
      keys.push(name);
    }
  }
  return keys;
};

// Return a string reflecting internal key-value pairs.
UrlHash.prototype.encode = function() {
  return _encode(this.dict);
};

// Useful for AJAX navigation.  If UrlHash is the state of the current page,
// then we override the state with 'attrs' and then return a serialized query
// fragment.  
UrlHash.prototype.modifyAndEncode = function(attrs) {
  var copy = {}
  // NOTE: Object.assign is ES6-only
  // https://googlechrome.github.io/samples/object-assign-es6/
  Object.assign(copy, this.dict, attrs);
  return _encode(copy);
};

