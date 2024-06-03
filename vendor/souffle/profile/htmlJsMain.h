/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2017, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

#include <string>

namespace souffle {
namespace profile {
namespace html {
std::string jsMain = R"___(
function changeSelectedRel(id) {
    selected.rel = id;
    highlightRow();
    genRulesOfRelations();
}

function changeSelectedRul(id) {
    selected.rul = id;
    highlightRow();
    genRulVer();
    genAtomVer();
}

function goBack() {
    if (came_from==="rel") {
        document.getElementById("rel_tab").click();
    } else if (came_from==="rul") {
        document.getElementById("rul_tab").click();
    }
}

function highlightRow() {
    var i;
    for (i=0;i<document.getElementsByClassName("rel_row").length;i++) {
        document.getElementsByClassName("rel_row")[i].style.background = "rgba(255,255,0,0)";
    }
    for (i=0;i<document.getElementsByClassName("rul_row").length;i++) {
        document.getElementsByClassName("rul_row")[i].style.background = "rgba(255,255,0,0)";
    }
    if (selected.rul) {
        document.getElementById(selected.rul).style.background = "rgba(255,255,0,0.2)";
    }
    if (selected.rel) {
        document.getElementById(selected.rel).style.background = "rgba(255,255,0,0.2)";
    }
}


function graphRel() {
    if (!selected.rel) {
        alert("please select a relation to graph");
        return;
    }

    graph_vals.labels = [];
    graph_vals.tot_t = [];
    graph_vals.tuples = [];
    for (var j = 0; j < data.rel[selected.rel][10].tot_t.length; j++) {
        graph_vals.labels.push(j.toString());
        graph_vals.tot_t.push(
            data.rel[selected.rel][10].tot_t[j]
        );
        graph_vals.tuples.push(
            data.rel[selected.rel][10].tuples[j]
        )
    }

    document.getElementById('chart_tab').click();
    drawGraph();
}

function graphIterRul() {
    if (!selected.rul || selected.rul[0]!='C') {
        alert("Please select a recursive rule (ID starts with C) to graph.");
        return;
    }

    came_from = "rul";

    graph_vals.labels = [];
    graph_vals.tot_t = [];
    graph_vals.tuples = [];
    for (var j = 0; j < data.rul[selected.rul][10].tot_t.length; j++) {
        graph_vals.labels.push(j.toString());
        graph_vals.tot_t.push(
            data.rul[selected.rul][10].tot_t[j]
        );
        graph_vals.tuples.push(
            data.rul[selected.rul][10].tuples[j]
        )
    }

    document.getElementById('chart_tab').click();
    drawGraph();
}


function graphUsages() {
    graph_vals.labels = [];
    graph_vals.cpu = [];
    graph_vals.rss = [];
    var interval = Math.ceil(data.usage.length / 8);
    for (var j = 0; j < data.usage.length; j++) {
        graph_vals.labels.push(
            j % interval == 0 ? data.usage[j][0] : "");
        graph_vals.cpu.push(
            {meta: data.usage[j][4], value: (data.usage[j][1] + data.usage[j][2]).toString()});
        graph_vals.rss.push(
            {meta: data.usage[j][4], value: data.usage[j][3].toString()});
    }

    var options = {
        height: "calc((100vh - 167px) / 2)",
        axisY: {
            labelInterpolationFnc: function (value) {
                return value.toFixed(0) + '%';
            }
        },
        axisX: {
            labelInterpolationFnc: function (value) {
                if (!value) {
                    return "";
                }
                return humanise_time(value);
            }
        },
        plugins: [Chartist.plugins.tooltip({tooltipFnc: function (meta, value) {
                value = Number(value);
                return meta + '<br/>' + value.toFixed(0) + '%';}})]
    };

    new Chartist.Bar(".ct-chart-cpu", {
        labels: graph_vals.labels,
        series: [graph_vals.cpu],
    }, options);

    options.axisY = {
        labelInterpolationFnc: function (value) {
            return minify_memory(value);
        },
    };

    options.plugins = [Chartist.plugins.tooltip({tooltipFnc: function(meta, value) {
                return meta + '<br/>' + minify_memory(value);}})]
    new Chartist.Bar(".ct-chart-rss", {
        labels: graph_vals.labels,
        series: [graph_vals.rss],
    }, options)
}

function drawGraph() {
    var options = {
        height: "calc((100vh - 167px) / 2)",
        axisY: {
            labelInterpolationFnc: function (value) {
                return humanise_time(value/1000000.0);
            }
        },
        axisX: {
            labelInterpolationFnc: function (value) {
                var n = Math.floor(graph_vals.labels.length/15);
                if (n>1) {
                    if (value%n == 0) {
                        return value;
                    }
                    return null;
                }
                return value;
            }
        },
        plugins: [Chartist.plugins.tooltip({
                  tooltipFnc: function(meta, value) {
                    return humanise_time(value / 1000000.0);
                  }
                  })]
    };

    new Chartist.Bar(".ct-chart1", {
        labels: graph_vals.labels,
        series: [graph_vals.tot_t],
    }, options);

    options.axisY = {
        labelInterpolationFnc: function (value) {
            return minify_numbers(value);
        }
    };
    options.plugins = [Chartist.plugins.tooltip({
                  tooltipFnc: function(meta, value) {
                    return minify_numbers(value) + " tuples";
                  }
                  })]

    new Chartist.Bar(".ct-chart2", {
        labels: graph_vals.labels,
        series: [graph_vals.tuples],
    }, options)
}


function changeTab(event, change_to) {
    if (change_to === "Chart") {
        document.getElementById("chart-tab").style.display = "block";
    } else {
        document.getElementById("chart-tab").style.display = "none";
    }
    var c, d, e;
    d = document.getElementsByClassName("tabcontent");
    for (c = 0; c < d.length; c++) {
        d[c].style.display = "none";
    }

    e = document.getElementsByClassName("tablinks");
    for (c = 0; c < e.length; c++) {
        e[c].className = e[c].className.replace(" active", "");
    }

    document.getElementById(change_to).style.display = "block";
    event.currentTarget.className += " active"
}


function toggle_precision() {
    precision=!precision;
    flip_table_values(document.getElementById("Rel_table"));
    flip_table_values(document.getElementById("Rul_table"));
    flip_table_values(document.getElementById("rulesofrel_table"));
    flip_table_values(document.getElementById("rulvertable"));
}

function flip_table_values(table) {
    var i,j,cell;
    for (i in table.rows) {
        if (!table.rows.hasOwnProperty(i)) continue;
        for (j in table.rows[i].cells) {
            if (! table.rows[i].cells.hasOwnProperty(j)) continue;
            cell = table.rows[i].cells[j];
            if (cell.className === "time_cell") {
                val = cell.getAttribute('data-sort');
                cell.innerHTML = humanise_time(parseFloat(val));
            } else if (cell.className === "int_cell") {
                val = cell.getAttribute('data-sort');
                cell.innerHTML = minify_numbers(parseInt(val));
            }
        }
    }
}

function create_cell(type, value, perc_total) {
    cell = document.createElement("td");

    if (type === "text") {
        cell.className = "text_cell";
        text_span = document.createElement("span");
        text_span.innerHTML = value;
        cell.appendChild(text_span);
    } else if (type === "code_loc") {
        cell.className = "text_cell";
        text_span = document.createElement("span");
        text_span.innerHTML = value;
        cell.appendChild(text_span);
        if (data.hasOwnProperty("code"))
            text_span.onclick = function() {view_code_snippet(value);}
    } else if (type === "id") {
        cell.innerHTML = value;
    } else if (type === "time") {
        cell.innerHTML = humanise_time(value);
        cell.setAttribute('data-sort', value);
        cell.className = "time_cell";
    } else if (type === "int") {
        cell.innerHTML = minify_numbers(value);
        cell.setAttribute('data-sort', value);
        cell.className = "int_cell";
    } else if (type === "perc") {
        div = document.createElement("div");
        div.className = "perc_time";
        if (perc_total == 0) {
            div.style.width = "0%";
            div.innerHTML = "0";
        } else if (isNaN(value)) {
            div.style.width = "0%";
            div.innerHTML = "NaN";
        } else {
            div.style.width = parseFloat(value) / perc_total * 100 + "%";
            div.innerHTML = clean_percentages(parseFloat(value) / perc_total * 100);
        }
        cell.appendChild(div);
    }
    return cell;
}


function generate_table(data_format,body_id,data_key) {
    var item,i;
    var perc_totals = [];

    for (i in data_format) {
        if (!data_format.hasOwnProperty(i)) continue;
        if (data_format[i][0] === "perc") {
            perc_totals.push([data_format[i][1],data_format[i][2],0]);
        }
    }

    for (item in data[data_key]) {
        if (data[data_key].hasOwnProperty(item)) {
            for (i in perc_totals) {
                if (!isNaN(data[data_key][item][perc_totals[i][1]])) {
                    perc_totals[i][2] += data[data_key][item][perc_totals[i][1]];
                }
            }
        }
    }


    table_body = document.getElementById(body_id);
    table_body.innerHTML = "";
    for (item in data[data_key]) {
        if (data[data_key].hasOwnProperty(item)) {
            row = document.createElement("tr");
            row.id = item;

            if (data_key === "rel") {
                row.className = "rel_row";
                row.onclick = function () {
                    changeSelectedRel(this.id);
                };
            } else if (data_key === "rul") {
                row.className = "rul_row";
                row.onclick = function () {
                    changeSelectedRul(this.id);
                };
            }
            perc_counter = 0;
            for (i in data_format) {
                if (!data_format.hasOwnProperty(i)) continue;
                if (data_format[i][0] === "perc") {
                    cell = create_cell(data_format[i][0], data[data_key][item][data_format[i][2]], perc_totals[perc_counter++][2]);
                } else {
                    cell = create_cell(data_format[i][0], data[data_key][item][data_format[i][1]]);
                }
                row.appendChild(cell);
            }
            table_body.appendChild(row);
        }
    }
}

function gen_rel_table() {
    generate_table([["text",0],["id",1],["time",2],["time",3],["time",4],
        ["time",5],["int",6],["int", 7],["perc","float",2],["perc","int",6],["code_loc",8]],
        "Rel_table_body",
    "rel");
}

function gen_rul_table() {
    generate_table([["text",0],["id",1],["time",2],["time",3],["time",4],
            ["int",5],["perc","float",2],["perc","int",5],["code_loc",6]],
        "Rul_table_body",
        "rul");
}

function gen_top_rel_table() {
    generate_table([["text",0],["id",1],["time",2],["time",3],["time",4],
        ["time",5],["int",6],["int",7],["perc","float",2],["perc","int",6],["code_loc",8]],
        "top_rel_table_body",
    "topRel");
}

function gen_top_rul_table() {
    generate_table([["text",0],["id",1],["time",2],["time",3],["time",4],
            ["int",5],["perc","float",2],["perc","int",5],["code_loc",6]],
        "top_rul_table_body",
        "topRul");
}


function genRulesOfRelations() {
    var data_format = [["text",0],["id",1],["time",2],["time",3],["time",4],
            ["int",5],["perc","float",2],["perc","int",5],["code_loc",6]];
    var rules = data.rel[selected.rel][9];
    var perc_totals = [];
    var row, cell, perc_counter, table_body, i, j;
    table_body = document.getElementById("rulesofrel_body");
    table_body.innerHTML = "";

    for (i in data_format) {
        if (!data_format.hasOwnProperty(i)) continue;
        if (data_format[i][0] === "perc") {
            perc_totals.push([data_format[i][1],data_format[i][2],0]);
        }
    }

    for (item in rules) {
        if (data.rul[rules[item]].hasOwnProperty(item)) {
            for (i in perc_totals) {
                if (!isNaN(data.rul[rules[item]][perc_totals[i][1]])) {
                    perc_totals[i][2] += data.rul[rules[item]][perc_totals[i][1]];
                }
            }
        }
    }

    for (j=0; j<rules.length; j++) {
        row = document.createElement("tr");
        perc_counter=0;
        for (i in data_format) {
            if (!data_format.hasOwnProperty(i)) continue;
            if (data_format[i][0] === "perc") {
                cell = create_cell(data_format[i][0], data.rul[rules[j]][data_format[i][2]], perc_totals[perc_counter++][2]);
            } else {
                cell = create_cell(data_format[i][0], data.rul[rules[j]][data_format[i][1]]);
            }
            row.appendChild(cell);
        }
        table_body.appendChild(row);
    }

    document.getElementById("rulesofrel").style.display = "block";
}

function genRulVer() {
    var data_format = [["text",0],["id",1],["time",2],["time",3],["time",4],
        ["int",5],["int",7],["perc","float",2],["perc","int",5],["code_loc",6]];
    var rules = data.rul[selected.rul][7];
    var perc_totals = [];
    var row, cell, perc_counter, table_body, i, j;
    table_body = document.getElementById("rulver_body");
    table_body.innerHTML = "";

    for (i in data_format) {
        if (!data_format.hasOwnProperty(i)) continue;
        if (data_format[i][0] === "perc") {
            if (!isNaN(data.rul[selected.rul][data_format[i][2]])) {
                perc_totals.push([data_format[i][1], data_format[i][2], data.rul[selected.rul][data_format[i][2]]]);
            }
        }
    }

    row = document.createElement("tr");
    for (i in data_format) {
        if (!data_format.hasOwnProperty(i)) continue;
        if (data_format[i][1] == 7) {
            cell = create_cell("text","-")
        } else if (data_format[i][0] === "perc") {
            cell = create_cell(data_format[i][0], 1, 1);
        } else {
            cell = create_cell(data_format[i][0], data.rul[selected.rul][data_format[i][1]]);
        }
        row.appendChild(cell);
    }
    table_body.appendChild(row);

    for (j=0; j<rules.length; j++) {
        row = document.createElement("tr");
        perc_counter=0;
        for (i in data_format) {
            if (!data_format.hasOwnProperty(i)) continue;
            if (data_format[i][0] === "perc") {
                cell = create_cell(data_format[i][0], rules[j][data_format[i][2]], perc_totals[perc_counter++][2]);
            } else {
                cell = create_cell(data_format[i][0], rules[j][data_format[i][1]]);
            }
            row.appendChild(cell);
        }
        table_body.appendChild(row);
    }

    document.getElementById("rulver").style.display = "block";
}
)___"
                     R"___(
function genAtomVer() {
    var atoms = data.atoms[selected.rul];
    var table_body = document.getElementById('atoms_body');
    table_body.innerHTML = "";

    for (i = 0; i < atoms.length; ++i) {
        var row = document.createElement("tr");
        row.appendChild(create_cell("text", atoms[i][1]));
        if (atoms[i][2] === undefined) {
            row.appendChild(create_cell("text", '--'));
        } else {
            row.appendChild(create_cell("int", atoms[i][2]));
        }
        row.appendChild(create_cell("int", atoms[i][3]));
        table_body.appendChild(row);
    }
    document.getElementById("atoms").style.display = "block";
}

function genConfig() {
    var table = document.createElement("table");
    {
        var header = document.createElement("thead");
        var headerRow = document.createElement("tr");
        var headerName = document.createElement("th");
        headerName.textContent = "Key";
        var headerValue = document.createElement("th");
        headerValue.textContent = "Value";

        headerRow.appendChild(headerName);
        headerRow.appendChild(headerValue);
        header.appendChild(headerRow);
        table.appendChild(header);
    }
    var body = document.createElement("tbody");
    for (i in data["configuration"]) {
        var row = document.createElement("tr");
        var name = document.createElement("td");
        if (i === "") {
            name.textContent = "Datalog input file";
        } else {
            name.textContent = i;
        }
        var value = document.createElement("td");
        value.textContent = data["configuration"][i];

        row.appendChild(name);
        row.appendChild(value);
        body.appendChild(row);
    }
    table.appendChild(body);
    return table;
}

function gen_top() {
    var statsElement, line1, line2;
    statsElement = document.getElementById("top-stats");
    line1 = document.createElement("p");
    line1.textContent = "Total runtime: " + humanise_time(data.top[0]) + " (" + data.top[0] + " seconds)";
    line2 = document.createElement("p");
    line2.textContent = "Total tuples: " + minify_numbers(data.top[1]) + " (" + data.top[1] + ")";
    line3 = document.createElement("p");
    line3.textContent = "Total loadtime: " + humanise_time(data.top[2]) + " (" + data.top[2] + " seconds)";
    line4 = document.createElement("p");
    line4.textContent = "Total savetime: " + humanise_time(data.top[3]) + " (" + data.top[3] + " seconds)";
    statsElement.appendChild(line1);
    statsElement.appendChild(line2);
    statsElement.appendChild(line3);
    statsElement.appendChild(line4);
    graphUsages();

    document.getElementById("top-config").appendChild(genConfig());
    gen_top_rel_table();
    gen_top_rul_table();
}

function view_code_snippet(value) {
    value = value.split(" ");
    value = value[value.length-1]; // get [num:num]
    value = value.slice(1); // cut out "["
    value = value.split(":");
    value = value[0];
    var targetLi = gen_code(parseInt(value));
    document.getElementById("code_tab").click();

    var list = document.getElementById("code-view");

    list.scrollTop = Math.max(21*parseInt(value) - 100, 0);

}


function gen_code(highlight_row) {
    var list, row, text, target_row;
    list = document.getElementById("code-list");
    list.innerHTML = "";
    if (!data.code) return;
    for (var i=0; i<data.code.length; i++) {
        row = document.createElement("li");
        row.className = "code-li";
        if (i+1 == highlight_row) {
            target_row = row;
            row.style.background = "#E0FFFF";
        }
        row.style.marginBottom = "0";
        text = document.createElement("span");
        text.className = "text-span";
        text.textContent = data.code[i];
        row.appendChild(text);
        list.appendChild(row);
    }
    document.getElementById("code-view").appendChild(list);
    return target_row;
}


var precision = !1;
var selected = {rel: !1, rul: !1};
var came_from = !1;
var graph_vals = {
    labels:[],
    tot_t:[],
    tuples:[]
};


function init() {
    gen_top();
    gen_rel_table();
    gen_rul_table();
    gen_code(-1)
    Tablesort(document.getElementById('Rel_table'),{descending: true});
    Tablesort(document.getElementById('Rul_table'),{descending: true});
    Tablesort(document.getElementById('rulesofrel_table'),{descending: true});
    Tablesort(document.getElementById('rulvertable'),{descending: true});
    document.getElementById("default").click();
    //document.getElementById("default").classList['active'] = !0;

}

init();
    )___";
}
}  // namespace profile
}  // namespace souffle
