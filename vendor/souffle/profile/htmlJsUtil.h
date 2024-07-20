#include <string>

namespace souffle {
namespace profile {
namespace html {
std::string jsUtil = R"___(
/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2017, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */


function clean_percentages(data) {
    if (data < 1) {
        return data.toFixed(3);
    }
    return data.toPrecision(3);
}

function humanise_time(time) {
    if (precision) return time.toString();
    if (time < 1e-9) {
        return '0';
    }
    if (time < 1) {
        milli = time * 1000.0;
        if (milli > 1) {
            return time.toFixed(3) + "s"
        }
        micro = milli * 1000.0;
        if (micro >= 1) {
            return micro.toFixed(1) + "µs"
        }
        return (micro*1000).toFixed(1) + "ns"
    } else {
        minutes = (time / 60.0);
        if (minutes < 3) return time.toPrecision(3) + "s";
        hours = (minutes / 60);
        if (hours < 3) return minutes.toFixed(2) + "m";
        days = (hours / 24);
        if (days < 3) return hours.toFixed(2) + "H";
        weeks = (days / 7);
        if (weeks < 3) return days.toFixed(2) + "D";
        year = (days / 365);
        if (year < 3) return weeks.toFixed(2) + "W";
        return year.toFixed(2) + "Y"
    }
}

function minify_memory(value) {
    if (value < 1024 * 10) {
        return value + 'B';
    } else if (value < 1024 * 1024 * 10) {
        return Math.round(value / 1024) + 'kB';
    } else if (value < 1024 * 1024 * 1024 * 10) {
        return Math.round(value / (1024 * 1024)) + 'MB';
    } else if (value < 1024 * 1024 * 1024 * 1024 * 10) {
        return Math.round(value / Math.round(1024 * 1024 * 1024)) + 'GB';
    } else {
        return Math.round(value / Math.round(1024 * 1024 * 1024 * 1024)) + 'TB';
    }
}

function minify_numbers(num) {
    if (precision) return num.toString();
    kilo = (num / 1000);
    if (kilo < 1) return num;
    mil = (kilo / 1000);
    if (mil < 1) return kilo.toPrecision(3) + "K";
    bil = (mil / 1000);
    if (bil < 1) return mil.toPrecision(3) + "M";
    tril = (bil / 1000);
    if (tril < 1) return bil.toPrecision(3) + "B";
    quad = (tril / 1000);
    if (quad < 1) return tril.toPrecision(3) + "T";
    quin = (quad / 1000);
    if (quin < 1) return quad.toPrecision(3) + "q";
    sex = (quin / 1000);
    if (sex < 1) return quin.toPrecision(3) + "Q";
    sept = (sex / 1000);
    if (sept < 1) return sex.toPrecision(3) + "s";
    return sept.toFixed(2) + "S"
}



(function () {
    var cleanNumber = function (x) {
        var num = x.slice(0, -1);
        var spec = x.slice(-1);
        if (spec == 'K') {
            return parseFloat(num) * 1e3;
        } else if (spec == 'M') {
            return parseFloat(num) * 1e6;
        } else if (spec == "B") {
            return parseFloat(num) * 1e9;
        } else if (spec == "T") {
            return parseFloat(num) * 1e12;
        } else if (spec == "q") {
            return parseFloat(num) * 1e15;
        } else if (spec == "Q") {
            return parseFloat(num) * 1e18;
        } else if (spec == "s") {
            return parseFloat(num) * 1e21;
        } else if (spec == "S") {
            return parseFloat(num) * 1e24;
        }
        return parseFloat(x);
    };
    var a = function (a) {
        return a;
    }, b = function (a, b) {
        return a = cleanNumber(a), b = cleanNumber(b), a = isNaN(a) ? 0 : a, b = isNaN(b) ? 0 : b, a - b
    };
    Tablesort.extend("number", function (a) {
        return a.match(/.*/)
    }, function (c, d) {
        return c = a(c), d = a(d), b(d, c)
    })
})();

(function () {
    var compare = function (a, b) {
        return a.localeCompare(b);
    };
    Tablesort.extend("text", function (a) {
        return a.match(/.*/)
    }, function (c, d) {
        return compare(d, c)
    })
})();

(function () {
    var cleanNumber = function (x) {
            if (x.slice(-1) == 'Y') {
                return parseFloat(x.slice(0, -1)) * 365 * 24 * 60 * 60;
            } else if (x.slice(-1) == 'W') {
                return parseFloat(x.slice(0, -1)) * 7 * 24 * 60 * 60;
            } else if (x.slice(-1) == "D") {
                return parseFloat(x.slice(0, -1)) * 24 * 60 * 60;
            } else if (x.slice(-1) == "H") {
                return parseFloat(x.slice(0, -1)) * 60 * 60;
            } else if (x.slice(-1) == "m") {
                return parseFloat(x.slice(0, -1)) * 60;
            } else if (x.slice(-2) == "µs") {
                return parseFloat(x.slice(0, -2)) / 1e6;
            } else if (x.slice(-2) == "ns") {
                return parseFloat(x.slice(0, -2)) / 1e9;
            } else if (x.slice(-1) == "s") {
                return parseFloat(x.slice(0, -1));
            }
            return parseFloat(x);
        },
        compareNumber = function (a, b) {
            a = isNaN(a) ? 0 : a;
            b = isNaN(b) ? 0 : b;
            return a - b;
        };
    Tablesort.extend('time', function (item) {
        return true;
    }, function (a, b) {
        a = cleanNumber(a);
        b = cleanNumber(b);
        return compareNumber(b, a);
    });
}());

)___";
}
}  // namespace profile
}  // namespace souffle
