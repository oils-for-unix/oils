

#include <string>

namespace souffle {
namespace profile {
namespace html {
std::string cssStyle = R"___(
a, abbr, acronym, address,
applet, article, aside, audio, b, big, blockquote, body, canvas, caption,
center, cite, code, dd, del, details, dfn, dl, dt, em, embed, fieldset,
figcaption, figure, footer, form, h1, h2, h3, h4, h5, h6, header, html,
i, iframe, img, ins, kbd, label, legend, li, mark, menu, nav,
object, ol, output, p, pre, q, ruby, s, samp, section, small,
span, strike, strong, sub, summary, sup, table, tbody, td,
tfoot, th, thead, time, tr, tt, u, ul, var, video {
    margin: 0;
    padding: 0;
    border: 0;
    font: inherit;
    vertical-align: baseline;
}

th[role=columnheader]:not(.no-sort) {
    cursor: pointer;
}

th[role=columnheader]:not(.no-sort):after {
    content: '';
    float: right;
    margin-top: 7px;
    border-width: 0 4px 4px;
    border-style: solid;
    border-color: #404040 transparent;
    visibility: hidden;
    opacity: 0;
    -webkit-user-select: none;
    -moz-user-select: none;
    user-select: none;
}

th[aria-sort=ascending]:not(.no-sort):after {
    border-bottom: none;
    border-width: 4px 4px 0;
}

th[aria-sort]:not(.no-sort):after {
    visibility: visible;
    opacity: 0.4;
}

th[role=columnheader]:not(.no-sort):hover:after {
    visibility: visible;
    opacity: 1;
}

body,
h1 {
    font-size: 13px
}

article, aside, details, figcaption, figure, footer, header, menu, nav, section {
    display: block
}

body,
html {
    line-height: 1
}

ol,
ul {
    list-style: none
}

blockquote,
q {
    quotes: none
}

blockquote:after,
blockquote:before,
q:after,
q:before {
    content: none
}

:focus {
    outline: 0
}

*,
:after,
:before {
    box-sizing: border-box
}

body {
    margin: 0;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    line-height: 18px;
    color: #303030;
    background-color: #fafafa;
    -webkit-font-smoothing: antialiased;
    padding: 0
}

h1,
h2,
h3,
h4,
h5 {
    font-weight: 700;
    display: block;
    margin: 0 0 10px;
    text-align: center;
}

h1,
ul {
    margin: 0 0 20px
}

h1 {
    display: block;
    font-weight: 400;
    text-shadow: 0 1px 0 #fff
}

a,
strong,
table th {
    font-weight: 700
}

h1 span.description {
    color: #6d6d6d
}

h2 {
    font-size: 18px;
    line-height: 24px;
    margin: 20px 0 10px
}

h3 {
    font-size: 15px;
    margin: 20px 0
}

li {
    margin-left: 30px;
    margin-bottom: 3px
}

ul li {
    list-style: disc
}

ol li {
    list-style: decimal
}

a {
    color: #404040;
    text-decoration: none;
    border-bottom: 1px solid #ddd
}

a:hover {
    border-color: #d0d0d0
}

.notice {
    background: #ffa;
    border: 1px solid #cc7;
    display: block;
    padding: 10px;
    margin-bottom: 10px
}

.stretch {
    display: block;
    width: 100%
}

.pad1y {
    padding: 10px 0
}

.center {
    text-align: center
}

.content {
    margin-top: 40px;
    padding: 0 0 20px
}

table {
    background: #fff;
    max-width: 100%;
    border-spacing: 0;
    width: 100%;
    margin: 10px 0;
    border: 1px solid #ddd;
    border-collapse: separate;
    -webkit-box-shadow: 0 0 4px rgba(0, 0, 0, .1);
    -moz-box-shadow: 0 0 4px rgba(0, 0, 0, .1);
    box-shadow: 0 0 4px rgba(0, 0, 0, .1)
}

table td,
table th {
    position: relative;
    padding: 4px;
    line-height: 15px;
    text-align: left;
    border-top: 1px solid #ddd
}

.limiter,
header {
    margin: 0 auto;
    padding: 0 20px
}

table th {
    background: #eee;
    background: -webkit-gradient(linear, left top, left bottom, from(#f6f6f6), to(#eee));
    background: -moz-linear-gradient(top, #f6f6f6, #eee);
    text-shadow: 0 1px 0 #fff;
    vertical-align: bottom
}

table td {
    vertical-align: top
}

table tr {
    background: rgba(0, 255, 0, 0)
}

table tbody:first-child tr:first-child td,
table tbody:first-child tr:first-child th,
table thead:first-child tr td,
table thead:first-child tr th,
table thead:first-child tr:first-child th {
    border-top: 0
}

table tbody + tbody {
    border-top: 2px solid #ddd
}

table td + td,
table td + th,
table th + td,
table th + th {
    border-left: 1px solid #ddd
}

header {
    width: 960px
}

.limiter {
    width: 520px
}

.links {
    width: 480px;
    margin: 50px auto 0
}

.links a {
    width: 50%;
    float: left
}

a.button {
    background: #1F90FF;
    border: 1px solid #1f4fff;
    height: 40px;
    line-height: 38px;
    color: #fff;
    display: inline-block;
    text-align: center;
    padding: 0 10px;
    -webkit-border-radius: 1px;
    border-radius: 1px;
    -webkit-transition: box-shadow 150ms linear;
    -moz-transition: box-shadow 150ms linear;
    -o-transition: box-shadow 150ms linear;
    transition: box-shadow 150ms linear
}

pre,
pre code {
    line-height: 1.25em
}

a.button:hover {
background-color: #0081ff;
-webkit-box-shadow: 0 1px 5px rgba(0, 0, 0, .25);
box-shadow: 0 1px 5px rgba(0, 0, 0, .25);
border: 1px solid #1f4fff
}

a.button:active,
a.button:focus {
background: #0081ff;
-webkit-box-shadow: inset 0 1px 5px rgba(0, 0, 0, .25);
box-shadow: inset 0 1px 5px rgba(0, 0, 0, .25)
}

.options {
    margin: 10px 0 30px 15px
}

.options h3 {
    display: block;
    padding-top: 10px;
    margin-top: 20px
}

.options h3:first-child {
    border: none;
    margin-top: 0
}

code,
pre {
    font-family: Consolas, Menlo, 'Liberation Mono', Courier, monospace;
    word-wrap: break-word;
    color: #333
}

pre {
    font-size: 13px;
    background: #fff;
    padding: 10px 15px;
    margin: 10px 0;
    overflow: auto;
    -webkit-box-shadow: 0 1px 3px rgba(0, 0, 0, .3);
    box-shadow: 0 1px 3px rgba(0, 0, 0, .3)
}

code {
    font-size: 12px;
    border: 0;
    padding: 0;
    background: #e6e6e6;
    background: rgba(0, 0, 0, .08);
    box-shadow: 0 0 0 2px rgba(0, 0, 0, .08)
}

pre code {
    font-size: 13px;
    background: 0 0;
    box-shadow: none;
    border: none;
    padding: 0;
    margin: 0
}

.col12 {
    width: 100%
}

.col6 {
    width: 50%;
    float: left;
    display: block
}

#toolbar-button,
ul.tab li a {
    display: inline-block;
    text-align: center;
    text-decoration: none
}

.pill-group {
    margin: 40px 0 0
}

.pill-group a:first-child {
    border-radius: 20px 0 0 20px;
    border-right-width: 0
}

.pill-group a:last-child {
    border-radius: 0 20px 20px 0
}

#toolbar-button {
    background-color: #4CAF50;
    border: none;
    color: #fff;
    margin: 7px 12px;
    padding: 8px 14px;
    font-size: 32px
}

.tabcontent,
ul.tab {
    border: 1px solid #ccc
}

#toolbar-button:hover {
    background-color: #0081ff;
    -webkit-box-shadow: 0 1px 5px rgba(0, 0, 0, .25);
    box-shadow: 0 1px 5px rgba(0, 0, 0, .25)
}

#toolbar-button:active,
#toolbar-button:focus {
    background: #0081ff;
    -webkit-box-shadow: inset 0 1px 5px rgba(0, 0, 0, .25);
    box-shadow: inset 0 1px 5px rgba(0, 0, 0, .25)
}

ul.tab {
    margin: 0;
    padding: 0;
    overflow: hidden;
    border: 1px solid #ccc;
    background-color: #f1f1f1;
}

ul.tab li {
    float: left;
    list-style: none;
}

ul.tab li a {
    display: inline-block;
    color: black;
    text-align: center;
    padding: 14px 16px;
    text-decoration: none;
    transition: 0.3s;
    font-size: 17px;
}

ul.tab li a:hover {
    background-color: #ddd;
}

ul.tab li a:focus, .active {
    background-color: #ccc;
}

.tabcontent {
    display: none;
    padding: 6px 12px;
    border: 1px solid #ccc;
    border-top: none;
}

.rulesofrel {
    display: none;
    animation: fadeEffect 1s
}

.RulVerTable {
    display: none;
    -webkit-animation: fadeEffect 1s;
    animation: fadeEffect 1s
}

@-webkit-keyframes fadeEffect {
    from {
        opacity: 0
    }
    to {
        opacity: 1
    }
}

@keyframes fadeEffect {
    from {
        opacity: 0
    }
    to {
        opacity: 1
    }
}

.rulesofrel,
.tabcontent {
    -webkit-animation: fadeEffect 1s
}

.perc_time,
.perc_tup {
    padding: 0;
    margin: 0;
    background: #aaf;
    width: 100%;
    height: 30px;
    font: inherit;
    font-weight: 700;
    color: #000
}

.text_cell {
    position: relative;
}

.text_cell span {
    word-break: break-all;
    position: absolute;
    width: 95%;
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
}

.text_cell span:hover {
    word-break: break-all;
    position: absolute;
    width: 95%;
    height: auto;
    text-overflow: initial;
    white-space: normal;
    overflow: visible;
    background: #fff;
    z-index: 10;
}

th:last-child {
    width: 20%;
}

th:first-child {
    width: 80%;
}

.table_wrapper {
    max-height: 50vh;
    overflow-y: scroll;
}

/* chartist tooltip plugin css */
.chartist-tooltip {
    position: absolute;
    display: none;
    opacity: 0;
    min-width: 5em;
    padding: .5em;
    background: #F4C63D;
    color: #453D3F;
    font-family: Oxygen, Helvetica, Arial, sans-serif;
    font-weight: 700;
    text-align: center;
    pointer-events: none;
    z-index: 1;
    -webkit-transition: opacity .2s linear;
    -moz-transition: opacity .2s linear;
    -o-transition: opacity .2s linear;
    transition: opacity .2s linear;
}

.chartist-tooltip:before {

    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    width: 0;
    height: 0;
    margin-left: -15px;
    border: 15px solid transparent;
    border-top-color: #F4C63D;
}

.chartist-tooltip.tooltip-show {
    display: inline-block;
    opacity: 1;
}

.ct-area, .ct-line {
    pointer-events: none;
}

button {
    font-family: inherit;
    font-size: 100%;
    padding: .5em 1em;
    color: #444;
    color: rgba(0, 0, 0, .8);
    border: 1px solid #999;
    background-color: #E6E6E6;
    text-decoration: none;
    border-radius: 2px
}
button:hover {
    filter: alpha(opacity=90);
    background-image: -webkit-linear-gradient(transparent, rgba(0, 0, 0, .05) 40%, rgba(0, 0, 0, .1));
    background-image: linear-gradient(transparent, rgba(0, 0, 0, .05) 40%, rgba(0, 0, 0, .1))
}

button {
    border: none;
    display: inline-block;
    zoom: 1;
    line-height: normal;
    white-space: nowrap;
    vertical-align: middle;
    text-align: center;
    cursor: pointer;
    -webkit-user-drag: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
    box-sizing: border-box;
}

#Help p {
    margin-bottom: 1em;
}

#code-list {
    background: #AAA;
    padding-left: 2em;
    color: #666;
}

.code-li {
    background: #FAFAFA;
    marginBottom: 0;
}

#code-view {
    overflow: auto;
    height: calc( 100vh - 160px );
    width: calc( 100vw - 25px );
    font-family: Consolas, Menlo, Monaco, Lucida Console,'Bitstream Vera Sans Mono','Courier',monospace;
    line-height: 21px;
}

#code-view .text-span {
    white-space: nowrap;
    padding-left: 6px;
    color: #666;
}

#code-view .ol li:before  {
    color: #666;
    background: #AAA;
}

.code-li:hover {
    background: #eacf7d;
}

.number-span {
    content: counter(item) ". ";
    counter-increment: item;
    list-style:decimal;
    width: 60px;
}
)___";
}
}  // namespace profile
}  // namespace souffle
