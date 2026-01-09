#!/usr/bin/env python3

import io
import os
import os.path
import subprocess
import sys
import json

from os import listdir
from time import strftime

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
PARSERS_DIR = os.path.join(BASE_DIR, "parsers")
TEST_CASES_DIR_PATH = os.path.join(BASE_DIR, "test_parsing")
LOGS_DIR_PATH = os.path.join(BASE_DIR, "results")
LOG_FILENAME = "logs.txt"
LOG_FILE_PATH = os.path.join(LOGS_DIR_PATH, LOG_FILENAME)

INVALID_BINARY_FORMAT = 8
BAD_CPU_TYPE = 86

programs = {
    # "Awk JSON.awk busybox":
    #     {
    #         "url":"https://github.com/step-/JSON.awk",
    #         "commands":["/bin/busybox", "awk", "-f", os.path.join(PARSERS_DIR, "test_JSON.awk", "JSON-busybox.awk")]
    #     },
    # "Awk JSON.awk gawk POSIX":
    #     {
    #         "url":"https://github.com/step-/JSON.awk",
    #         "commands":["/usr/bin/gawk", "--posix", "-f", os.path.join(PARSERS_DIR, "test_JSON.awk", "JSON.awk")]
    #     },
    "Awk JSON.awk gawk":
        {
            "url":"https://github.com/step-/JSON.awk",
            "commands":["/usr/bin/gawk", "-f", os.path.join(PARSERS_DIR, "test_JSON.awk", "JSON.awk")]
        },
    # "Awk JSON.awk mawk":
    #     {
    #         "url":"https://github.com/step-/JSON.awk",
    #         "commands":["/usr/bin/mawk", "-f", os.path.join(PARSERS_DIR, "test_JSON.awk", "callbacks.awk"), "-f", os.path.join(PARSERS_DIR, "test_JSON.awk", "JSON.awk")]
    #     },
    "Bash JSON.sh 2016-08-12":
        {
            "url":"https://github.com/dominictarr/JSON.sh",
            "commands":[os.path.join(PARSERS_DIR, "test_Bash_JSON/JSON.sh")],
            "use_stdin":True
        },
   #  "R rjson":
   #      {
   #          "url":"",
   #          "commands":["/usr/local/bin/RScript", os.path.join(PARSERS_DIR, "test_rjson.r")]
   #      },
   #  "R jsonlite":
   #      {
   #          "url":"",
   #          "commands":["/usr/local/bin/RScript", os.path.join(PARSERS_DIR, "test_jsonlite.r")]
   #      },
   # "Obj-C JSONKit":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_JSONKit/bin/test-JSONKit")]
   #     },
   # "Obj-C Apple NSJSONSerialization":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_ObjCNSJSONSerializer/bin/test_ObjCNSJSONSerializer")]
   #     },
   # "Obj-C TouchJSON":
   #     {
   #         "url":"https://github.com/TouchCode/TouchJSON",
   #         "commands":[os.path.join(PARSERS_DIR, "test_TouchJSON/bin/test_TouchJSON")]
   #     },
   # "Obj-C SBJSON 4.0.3":
   #     {
   #         "url":"https://github.com/stig/json-framework",
   #         "commands":[os.path.join(PARSERS_DIR, "test_SBJSON_4_0_3/bin/test_sbjson")]
   #     },
   # "Obj-C SBJSON 4.0.4":
   #     {
   #         "url":"https://github.com/stig/json-framework",
   #         "commands":[os.path.join(PARSERS_DIR, "test_SBJSON_4_0_4/bin/test_sbjson")]
   #     },
   # "Obj-C SBJson 5.0.0":
   #     {
   #         "url":"https://github.com/stig/json-framework",
   #         "commands":[os.path.join(PARSERS_DIR, "test_SBJson_5_0_0/bin/test_sbjson")]
   #     },
   # "Go 1.7.1":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_go/test_json")]
   #     },
   #  "Zig 0.8.0-dev.1354+081698156":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_zig/test_json")]
   #     },
   # "Free Pascal fcl-json":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_fpc/test_json")]
   #     },
   # "Xidel Internet Tools":
   #     {
   #         "url":"http://www.videlibri.de/xidel.html",
   #         "commands":["/usr/bin/env", "xidel", "--input-format=json-strict", "-e=."]
   #     },
   # "Lua JSON 20160916.19":
   #     {
   #         "url":"http://regex.info/blog/lua/json",
   #         "commands":["/usr/local/bin/lua", os.path.join(PARSERS_DIR, "test_Lua_JSON/test_JSON.lua")]
   #     },
   # "Lua dkjson":
   #     {
   #         "url":"http://dkolf.de/src/dkjson-lua.fsl/home",
   #         "commands":["/usr/local/bin/lua", os.path.join(PARSERS_DIR, "test_dkjson.lua")]
   #     },
   # "Ruby":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/env", "ruby", os.path.join(PARSERS_DIR, "test_json.rb")]
   #     },
   # "Ruby regex":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/env", "ruby", os.path.join(PARSERS_DIR, "test_json_re.rb")]
   #     },
   # "Ruby Yajl":
   #     {
   #         "url":"https://github.com/brianmario/yajl-ruby",
   #         "commands":["/usr/bin/env", "ruby", os.path.join(PARSERS_DIR, "test_yajl.rb")]
   #     },
   # "Ruby Oj (strict mode)":
   #     {
   #         "url":"https://github.com/ohler55/oj",
   #         "commands":["/usr/bin/env", "ruby", os.path.join(PARSERS_DIR, "test_oj_strict.rb")]
   #     },
   # "Ruby Oj (compat mode)":
   #     {
   #         "url":"https://github.com/ohler55/oj",
   #         "commands":["/usr/bin/env", "ruby", os.path.join(PARSERS_DIR, "test_oj_compat.rb")]
   #     },
   # "Crystal":
   #     {
   #         "url":"https://github.com/crystal-lang/crystal",
   #         "commands":[os.path.join(PARSERS_DIR, "test_json_cr")]
   #     },
   # "JavaScript":
   #     {
   #         "url":"",
   #         "commands":["/usr/local/bin/node", os.path.join(PARSERS_DIR, "test_json.js")]
   #     },
   # "Python 2.7.10":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/python", os.path.join(PARSERS_DIR, "test_json.py")]
   #     },
   # "Python 3.5.2":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/env", "python3.5", os.path.join(PARSERS_DIR, "test_json.py")]
   #     },
   # "Python cjson 1.10": # pip install cjson
   #     {
   #         "url":"https://pypi.python.org/pypi/python-cjson",
   #         "commands":["/usr/bin/python", os.path.join(PARSERS_DIR, "test_cjson.py")]
   #     },
   # "Python ujson 1.35": # pip install ujson
   #     {
   #         "url":"https://pypi.python.org/pypi/ujson",
   #         "commands":["/usr/bin/python", os.path.join(PARSERS_DIR, "test_ujson.py")]
   #     },
   # "Python simplejson 3.10": # pip install simplejson
   #     {
   #         "url":"https://pypi.python.org/pypi/simplejson",
   #         "commands":["/usr/bin/python", os.path.join(PARSERS_DIR, "test_simplejson.py")]
   #     },
   # "Python demjson 2.2.4": # pip install demjson
   #     {
   #         "url":"https://pypi.python.org/pypi/demjson",
   #         "commands":["/usr/bin/python", os.path.join(PARSERS_DIR, "test_demjson.py")]
   #     },
   # "Python demjson 2.2.4 (py3)": # pip install demjson
   #     {
   #         "url":"https://pypi.python.org/pypi/demjson",
   #         "commands":["/usr/bin/env", "python3.5", os.path.join(PARSERS_DIR, "test_demjson.py")]
   #     },
   # "Python demjson 2.2.4 (jsonlint)": # pip install demjson
   #     {
   #         "url":"https://pypi.python.org/pypi/demjson",
   #         "commands":["/usr/bin/env", "jsonlint", "--quiet", "--strict", "--allow=non-portable,duplicate-keys,zero-byte"]
   #     },
   # "Perl Cpanel::JSON::XS":
   #     {
   #         "url":"https://metacpan.org/pod/Cpanel::JSON::XS",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_cpanel_json_xs.pl")]
   #     },
   # "Perl JSON::Parse":
   #     {
   #         "url":"https://metacpan.org/pod/JSON::Parse",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_json_parse.pl")]
   #     },
   # "Perl JSON::PP": # part of default install in perl >= v5.14
   #     {
   #         "url":"https://metacpan.org/pod/JSON::PP",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_json_pp.pl")]
   #     },
   # "Perl JSON::SL":
   #     {
   #         "url":"https://metacpan.org/pod/JSON::SL",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_json_sl.pl")]
   #     },
   # "Perl JSON::Tiny":
   #     {
   #         "url":"https://metacpan.org/pod/JSON::Tiny",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_json_tiny.pl")]
   #     },
   # "Perl JSON::XS":
   #     {
   #         "url":"https://metacpan.org/pod/JSON::XS",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_json_xs.pl")]
   #     },
   # "Perl MarpaX::ESLIF::ECMA404":
   #     {
   #         "url":"http://metacpan.org/pod/MarpaX::ESLIF::ECMA404",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_marpax_eslif_ecma404.pl")]
   #     },
   # "Perl Mojo::JSON":
   #     {
   #         "url":"http://metacpan.org/pod/Mojo::JSON",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_mojo_json.pl")]
   #     },
   # "Perl Pegex::JSON":
   #     {
   #         "url":"http://metacpan.org/pod/Pegex::JSON",
   #         "commands":["/usr/bin/perl", os.path.join(PARSERS_DIR, "test_pegex_json.pl")]
   #     },
   # "PHP 5.5.36":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/php", os.path.join(PARSERS_DIR, "test_json.php")]
   #     },
   # "Swift Freddy 2.1.0":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_Freddy_2_1_0/bin/test_Freddy_2_1_0")]
   #     },
   # "Swift Freddy 20160830":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_Freddy_20160830/bin/test_Freddy")]
   #     },
   # "Swift Freddy 20161018":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_Freddy_20161018/bin/test_Freddy")]
   #     },
   # "Swift Freddy 20170118":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_Freddy_20170118/bin/test_Freddy")]
   #     },
   # "Swift PMJSON 1.1.0":
   #     {
   #         "url":"https://github.com/postmates/PMJSON",
   #         "commands":[os.path.join(PARSERS_DIR, "test_PMJSON_1_1_0/bin/test_PMJSON")]
   #     },
   # "Swift PMJSON 1.2.0":
   #     {
   #         "url":"https://github.com/postmates/PMJSON",
   #         "commands":[os.path.join(PARSERS_DIR, "test_PMJSON_1_2_0/bin/test_PMJSON")]
   #     },
   # "Swift PMJSON 1.2.1":
   #     {
   #         "url":"https://github.com/postmates/PMJSON",
   #         "commands":[os.path.join(PARSERS_DIR, "test_PMJSON_1_2_1/bin/test_PMJSON")]
   #     },
   # "Swift STJSON":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_STJSON/bin/STJSON")]
   #     },
   # "Swift Apple JSONSerialization":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test-AppleJSONSerialization/bin/test-AppleJSONSerialization")]
   #     },
   # "C pdjson 20170325":
   #     {
   #         "url":"https://github.com/skeeto/pdjson",
   #         "commands":[os.path.join(PARSERS_DIR, "test_pdjson/bin/test_pdjson")]
   #     },
   # "C jsmn":
   #     {
   #         "url":"https://github.com/zserge/jsmn",
   #         "commands":[os.path.join(PARSERS_DIR, "test_jsmn/bin/test_jsmn")]
   #     },
   # "C jansson":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_jansson/bin/test_jansson")]
   #     },
   # "C JSON Checker":
   #     {
   #         "url":"http://www.json.org/JSON_checker/",
   #         "commands":[os.path.join(PARSERS_DIR, "test_jsonChecker/bin/jsonChecker")]
   #     },
   # "C JSON Checker 2":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_jsonChecker2/bin/jsonChecker2")]
   #     },
   # "C JSON Checker 20161111":
   #     {
   #         "url":"https://github.com/douglascrockford/JSON-c",
   #         "commands":[os.path.join(PARSERS_DIR, "test_jsonChecker20161111/bin/jsonChecker20161111")]
   #     },
   # "C++ sajson 20170724":
   #     {
   #         "url":"https://github.com/chadaustin/sajson",
   #         "commands":[os.path.join(PARSERS_DIR, "test_sajson_20170724/bin/test_sajson")]
   #     },
   # "C ccan":
   #     {
   #         "url":"",
   #         "commands":[os.path.join(PARSERS_DIR, "test_ccan_json/bin/test_ccan")]
   #     },
   # "C cJSON 20160806":
   #     {
   #         "url":"https://github.com/DaveGamble/cJSON",
   #         "commands":[os.path.join(PARSERS_DIR, "test_cJSON_20160806/bin/test_cJSON")]
   #     },
   # "C cJSON 1.7.3":
   #     {
   #         "url":"https://github.com/DaveGamble/cJSON",
   #         "commands":[os.path.join(PARSERS_DIR, "test_cJSON_1_7_3/bin/test_cJSON")]
   #     },
   # "C JSON-C":
   #     {
   #         "url":"https://github.com/json-c/json-c",
   #         "commands":[os.path.join(PARSERS_DIR, "test_json-c/bin/test_json-c")]
   #     },
   # "C JSON Parser by udp":
   #     {
   #         "url":"https://github.com/udp/json-parser",
   #         "commands":[os.path.join(PARSERS_DIR, "test_json-parser/bin/test_json-parser")]
   #     },
   # "C++ nlohmann JSON 20190718":
   #     {
   #         "url":"https://github.com/nlohmann/json/",
   #         "commands":[os.path.join(PARSERS_DIR, "test_nlohmann_json_20190718/bin/test_nlohmann_json")]
   #     },
   # "C++ RapidJSON 20170724":
   #     {
   #         "url":"https://github.com/miloyip/rapidjson",
   #         "commands":[os.path.join(PARSERS_DIR, "test_rapidjson_20170724/bin/test_rapidjson")]
   #     },
   # "Rust json-rust":
   #     {
   #         "url":"https://github.com/maciejhirsz/json-rust",
   #         "commands":[os.path.join(PARSERS_DIR, "test_json-rust/target/debug/tj")]
   #     },
   # "Rust rustc_serialize::json":
   #     {
   #         "url":"https://doc.rust-lang.org/rustc-serialize/rustc_serialize/json/index.html",
   #         "commands":[os.path.join(PARSERS_DIR, "test_json-rustc_serialize/rj/target/debug/rj")]
   #     },
   # "Rust serde_json":
   #     {
   #         "url":"https://github.com/serde-rs/json",
   #         "commands":[os.path.join(PARSERS_DIR, "test_json-rust-serde_json/rj/target/debug/rj")]
   #     },
   # "Java json-simple 1.1.1":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_simple_json_1_1_1/TestJSONParsing.jar")]
   #     },
   # "Java org.json 2016-08-15":
   #     {
   #         "url":"https://github.com/stleary/JSON-java",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_org_json_2016_08/TestJSONParsing.jar")]
   #     },
   # "Java gson 2.7":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_gson_2_7/TestJSONParsing.jar")]
   #     },
   # "Java BFO v1":
   #     {
   #         "url":"https://github.com/faceless2/json",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_bfo/TestJSONParsing.jar")]
   #     },
   # "Java com.leastfixedpoint.json 1.0":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_com_leastfixedpoint_json_1_0/TestJSONParsing.jar")]
   #     },
   # "Java Jackson 2.8.4":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_jackson_2_8_4/TestJSONParsing.jar")]
   #     },
   # "Java JsonTree 0.5":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_json_tree/TestJSONParsing.jar")]
   #     },
   # "Scala Dijon 0.3.0":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_scala_dijon_0.3.0/target/scala-2.13/TestJSONParsing.jar")]
   #     },
   # "Java Mergebase Java2Json 2019.09.09":
   #     {
   #         "url":"https://github.com/mergebase/Java2Json",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_mergebase_json_2019_09_09/TestJSONParsing.jar")]
   #     },
   # "Java nanojson 1.0":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_nanojson_1_0/TestJSONParsing.jar")]
   #     },
   # "Java nanojson 1.1":
   #     {
   #         "url":"",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_nanojson_1_1/TestJSONParsing.jar")]
   #     },
   #  "Java Actson 1.2.0":
   #     {
   #         "url":"https://github.com/michel-kraemer/actson",
   #         "commands":["/usr/bin/java", "-jar", os.path.join(PARSERS_DIR, "test_java_actson_1_2_0/TestJSONParsing.jar")]
   #     },
   # "Haskell Aeson 0.11.2.1":
   #     {
   #         "url":"https://github.com/bos/aeson",
   #         "commands":[os.path.join(PARSERS_DIR, "test_haskell-aeson/testaeson")]
   #     },
   #  "OCaml Yojson":
   #     {
   #         "url":"https://github.com/mjambon/yojson",
   #         "commands":[os.path.join(PARSERS_DIR, "test_ocaml-yojson/testyojson")]
   #     },
   #  "OCaml Orsetto":
   #     {
   #         "url":"https://bitbucket.org/jhw/orsetto",
   #         "commands":[os.path.join(PARSERS_DIR, "test_ocaml_orsetto/test_orsetto_json")]
   #     },
   #  "Qt JSON":
   #      {
   #          "url":"",
   #          "commands":[os.path.join(PARSERS_DIR, "test_qt/test_qt")]
   #      },
   #  "C ConcreteServer":
   #      {
   #          "url":" https://github.com/RaphaelPrevost/ConcreteServer",
   #          "commands":[os.path.join(PARSERS_DIR, "test_ConcreteServer/json_checker")]
   #      },
   #  "Squeak JSON-tonyg":
   #      {
   #          "url":"http://www.squeaksource.com/JSON.html",
   #          "commands":[
   #                  os.path.join(PARSERS_DIR, "test_Squeak_JSON_tonyg/Squeak.app/Contents/MacOS/Squeak"),
   #                  "-headless", #<--optional
   #                  os.path.join(PARSERS_DIR, "test_Squeak_JSON_tonyg/Squeak5.1-16549-32bit.image"),
   #                  "test_JSON.st"
   #          ]
   #      },
   # ".NET Newtonsoft.Json 12.0.3":
   #     {
   #         "url":"http://www.newtonsoft.com/json",
   #         "setup":["dotnet", "build", "--configuration", "Release", os.path.join(PARSERS_DIR, "test_dotnet_newtonsoft/app.csproj")],
   #         "commands":["dotnet", os.path.join(PARSERS_DIR, "test_dotnet_newtonsoft/bin/Release/net5.0/app.dll")]
   #     },
   # ".NET System.Text.Json 5.0.0":
   #     {
   #         "url":"https://docs.microsoft.com/en-us/dotnet/api/system.text.json",
   #         "setup":["dotnet", "build", "--configuration", "Release", os.path.join(PARSERS_DIR, "test_dotnet_system_text_json/app.csproj")],
   #         "commands":["dotnet", os.path.join(PARSERS_DIR, "test_dotnet_system_text_json/bin/Release/net5.0/app.dll")]
   #     },
   # "Elixir Json":
   #       {
   #           "url":"https://github.com/cblage/elixir-json",
   #           "commands":[ os.path.join( PARSERS_DIR, "test_elixir_json/test_elixir_json") ]
   #       },
   # "Elixir ExJSON":
   #       {
   #           "url":"https://github.com/guedes/exjson",
   #           "commands":[ os.path.join( PARSERS_DIR, "test_elixir_exjson/test_elixir_exjson") ]
   #       },
   # "Elixir Poison":
   #       {
   #           "url":"https://github.com/devinus/poison",
   #           "commands":[ os.path.join( PARSERS_DIR, "test_elixir_poison/test_elixir_poison") ]
   #       },
   # "Elixir Jason":
   #       {
   #           "url":"https://github.com/michalmuskala/jason",
   #           "commands":[ os.path.join( PARSERS_DIR, "test_elixir_jason/test_elixir_jason") ]
   #       },
   # "Erlang Euneus":
   #       {
   #          "url":"https://github.com/williamthome/euneus",
   #          "commands":[ os.path.join( PARSERS_DIR, "test_erlang_euneus/test_erlang_euneus") ]
   #       },
   # "Nim":
   #       {
   #           "url":"http://nim-lang.org",
   #           "commands":[ os.path.join( PARSERS_DIR, "test_nim/test_json") ]
   #       },
   # "Swift JSON 20170522":
   #     {
   #         "url":"https://github.com/owensd/json-swift",
   #         "commands":[os.path.join(PARSERS_DIR, "test_json_swift_20170522/bin/json_swift")]
   #     },
   # "C++ nlohmann JSON 20190718":
   #     {
   #         "url":"https://github.com/nlohmann/json",
   #         "commands":[os.path.join(PARSERS_DIR, "test_nlohmann_json_20190718/bin/test_nlohmann_json")]
   #     },
   "Oils":
       {
           "url":"",
           "commands":[os.path.join(PARSERS_DIR, "test_oils.sh")]
       }
}

def run_tests(restrict_to_path=None, restrict_to_program=None):

    FNULL = open(os.devnull, 'w')
    log_file = open(LOG_FILE_PATH, 'w')

    prog_names = list(programs.keys())
    prog_names.sort()

    if isinstance(restrict_to_program, io.TextIOBase):
        restrict_to_program = json.load(restrict_to_program)

    if restrict_to_program:
        prog_names = filter(lambda x: x in restrict_to_program, prog_names)

    for prog_name in prog_names:
        d = programs[prog_name]

        url = d["url"]
        commands = d["commands"]
        setup = d.get("setup")
        if setup != None:
            print("--", " ".join(setup))
            try:
                subprocess.call(setup)
            except Exception as e:
                print("-- skip", e)
                continue

        for root, dirs, files in os.walk(TEST_CASES_DIR_PATH):
            json_files = (f for f in files if f.endswith(".json"))
            for filename in json_files:

                if restrict_to_path:
                    restrict_to_filename = os.path.basename(restrict_to_path)
                    if filename != restrict_to_filename:
                        continue

                file_path = os.path.join(root, filename)

                my_stdin = FNULL

                use_stdin = "use_stdin" in d and d["use_stdin"]
                if use_stdin:
                    my_stdin = open(file_path, "rb")
                    a = commands
                else:
                    a = commands + [file_path]

                #print("->", a)
                print("--", " ".join(a))

                try:
                    status = subprocess.call(
                        a,
                        stdin=my_stdin,
                        stdout=FNULL,
                        stderr=subprocess.STDOUT,
                        timeout=5
                    )
                    #print("-->", status)
                except subprocess.TimeoutExpired:
                    print("timeout expired")
                    s = "%s\tTIMEOUT\t%s" % (prog_name, filename)
                    log_file.write("%s\n" % s)
                    print("RESULT:", result)
                    continue
                except FileNotFoundError as e:
                    print("-- skip non-existing", e.filename)
                    break
                except OSError as e:
                    if e.errno == INVALID_BINARY_FORMAT or e.errno == BAD_CPU_TYPE:
                        print("-- skip invalid-binary", commands[0])
                        break
                    raise e

                if use_stdin:
                    my_stdin.close()

                result = None
                if status == 0:
                    result = "PASS"
                elif status == 1:
                    result = "FAIL"
                else:
                    result = "CRASH"

                s = None
                if result == "CRASH":
                    s = "%s\tCRASH\t%s" % (prog_name, filename)
                elif filename.startswith("y_") and result != "PASS":
                    s = "%s\tSHOULD_HAVE_PASSED\t%s" % (prog_name, filename)
                elif filename.startswith("n_") and result == "PASS":
                    s = "%s\tSHOULD_HAVE_FAILED\t%s" % (prog_name, filename)
                elif filename.startswith("i_") and result == "PASS":
                    s = "%s\tIMPLEMENTATION_PASS\t%s" % (prog_name, filename)
                elif filename.startswith("i_") and result != "PASS":
                    s = "%s\tIMPLEMENTATION_FAIL\t%s" % (prog_name, filename)

                if s != None:
                    print(s)
                    log_file.write("%s\n" % s)

    FNULL.close()
    log_file.close()

def f_underline_non_printable_bytes(bytes):

    html = ""

    has_non_printable_characters = False

    for b in bytes:

        is_not_printable = b < 0x20 or b > 0x7E

        has_non_printable_characters |= is_not_printable

        if is_not_printable:
            html += "<U>%02X</U>" % b
        else:
            html += "%c" % b

    if has_non_printable_characters:
        try:
            html += " <=> %s" % bytes.decode("utf-8", errors='ignore')
        except:
            pass

    if len(bytes) > 36:
        return "%s(...)" % html[:36]

    return html

def f_status_for_lib_for_file(json_dir, results_dir):

    txt_filenames = [f for f in listdir(results_dir) if f.endswith(".txt")]

    # comment to ignore some tests
    statuses = [
        "SHOULD_HAVE_FAILED",

        "SHOULD_HAVE_PASSED",
        "CRASH",

        "IMPLEMENTATION_FAIL",
        "IMPLEMENTATION_PASS",

        "TIMEOUT"
    ]

    d = {}
    libs = []

    for filename in txt_filenames:
        path = os.path.join(results_dir, filename)

        with open(path) as f:
            for l in f:
                comps = l.split("\t")
                if len(comps) != 3:
                    print("***", comps)
                    continue

                if comps[1] not in statuses:
                    print("-- unhandled status:", comps[1])

                (lib, status, json_filename) = (comps[0], comps[1], comps[2].rstrip())

                if lib not in libs:
                    libs.append(lib)

                json_path = os.path.join(TEST_CASES_DIR_PATH, json_filename)

                if json_path not in d:
                    d[json_path] = {}

                d[json_path][lib] = status

    return d, libs

def f_status_for_path_for_lib(json_dir, results_dir):

    txt_filenames = [f for f in listdir(results_dir) if f.endswith(".txt")]

    # comment to ignore some tests
    statuses = [
        "SHOULD_HAVE_FAILED",

        "SHOULD_HAVE_PASSED",
        "CRASH",

        "IMPLEMENTATION_FAIL",
        "IMPLEMENTATION_PASS",

        "TIMEOUT"

    ]

    d = {} # d['lib']['file'] = status

    for filename in txt_filenames:
        path = os.path.join(results_dir, filename)

        with open(path) as f:
            for l in f:
                comps = l.split("\t")
                if len(comps) != 3:
                    continue

                if comps[1] not in statuses:
                    #print "-- unhandled status:", comps[1]
                    continue

                (lib, status, json_filename) = (comps[0], comps[1], comps[2].rstrip())

                if lib not in d:
                    d[lib] = {}

                json_path = os.path.join(TEST_CASES_DIR_PATH, json_filename)

                d[lib][json_path] = status

    return d

def f_tests_with_same_results(libs, status_for_lib_for_file):

    tests_with_same_results = {} #{ {lib1:status, lib2:status, lib3:status} : { filenames } }

    files = list(status_for_lib_for_file.keys())
    files.sort()

    for f in files:
        prefix = os.path.basename(f)[:1]
        lib_status_for_file = []
        for l in libs:
            if l in status_for_lib_for_file[f]:
                status = status_for_lib_for_file[f][l]
                lib_status = "%s_%s" % (status, l)
                lib_status_for_file.append(lib_status)
        results = " || ".join(lib_status_for_file)
        if results not in tests_with_same_results:
            tests_with_same_results[results] = set()
        tests_with_same_results[results].add(f)

    r = []
    for k,v in tests_with_same_results.items():
        r.append((k,v))
    r.sort()

    return r

def generate_report(report_path, keep_only_first_result_in_set = False):

    (status_for_lib_for_file, libs) = f_status_for_lib_for_file(TEST_CASES_DIR_PATH, LOGS_DIR_PATH)

    status_for_path_for_lib = f_status_for_path_for_lib(TEST_CASES_DIR_PATH, LOGS_DIR_PATH)

    tests_with_same_results = f_tests_with_same_results(libs, status_for_lib_for_file)

    with open(report_path, 'w', encoding='utf-8') as f:

        f.write("""<!DOCTYPE html>

        <HTML>

        <HEAD>
            <TITLE>JSON Parsing Tests</TITLE>
            <LINK rel="stylesheet" type="text/css" href="style.css">
            <META charset="UTF-8">
        </HEAD>

        <BODY>
        """)

        prog_names = list(programs.keys())
        prog_names.sort()

        libs = list(status_for_path_for_lib.keys())
        libs.sort()

        title = "JSON Parsing Tests"
        if keep_only_first_result_in_set:
            title += ", Pruned"
        else:
            title += ", Full"
        f.write("<H1>%s</H1>\n" % title)
        f.write('<P>Appendix to: seriot.ch <A HREF="http://www.seriot.ch/parsing_json.php">Parsing JSON is a Minefield</A> http://www.seriot.ch/parsing_json.php</P>\n')
        f.write("<PRE>%s</PRE>\n" % strftime("%Y-%m-%d %H:%M:%S"))

        f.write("""<H4>Contents</H4>
        <OL>
        <LI><A HREF="#color_scheme">Color Scheme</A>
        <LI><A HREF="#all_results">Full Results</A>
        <LI><A HREF="#results_by_parser">Results by Parser</A>""")
        f.write("<UL>\n")
        for i, prog in enumerate(prog_names):
            f.write('    <LI><A HREF="#%d">%s</A>\n' % (i, prog))
        f.write("</OL>\n")

        f.write("""
        <A NAME="color_scheme"></A>
        <H4>1. Color scheme:</H4>
        <TABLE>
            <TR><TD class="EXPECTED_RESULT">expected result</TD><TR>
            <TR><TD class="SHOULD_HAVE_PASSED">parsing should have succeeded but failed</TD><TR>
            <TR><TD class="SHOULD_HAVE_FAILED">parsing should have failed but succeeded</TD><TR>
            <TR><TD class="IMPLEMENTATION_PASS">result undefined, parsing succeeded</TD><TR>
            <TR><TD class="IMPLEMENTATION_FAIL">result undefined, parsing failed</TD><TR>
            <TR><TD class="CRASH">parser crashed</TD><TR>
            <TR><TD class="TIMEOUT">timeout</TD><TR>
        </TABLE>
        """)

        ###

        f.write('<A NAME="all_results"></A>\n')
        f.write("<H4>2. Full Results</H4>\n")
        f.write("<TABLE>\n")

        f.write("    <TR>\n")
        f.write("        <TH></TH>\n")
        for lib in libs:
            f.write('        <TH class="vertical"><DIV>%s</DIV></TH>\n' % lib)
        f.write("        <TH></TH>\n")
        f.write("    </TR>\n")

        for (k, file_set) in tests_with_same_results:

            ordered_file_set = list(file_set)
            ordered_file_set.sort()

            if keep_only_first_result_in_set:
                ordered_file_set = [ordered_file_set[0]]

            for path in [path for path in ordered_file_set if os.path.exists(path)]:

                f.write("    <TR>\n")
                f.write('        <TD>%s</TD>' % os.path.basename(path))

                status_for_lib = status_for_lib_for_file[path]
                bytes = open(path, "rb").read()

                for lib in libs:
                    if lib in status_for_lib:
                        status = status_for_lib[lib]
                        f.write('        <TD class="%s">%s</TD>' % (status, ""))
                    else:
                        f.write('        <TD class="EXPECTED_RESULT"></TD>')
                f.write('        <TD>%s</TD>' % f_underline_non_printable_bytes(bytes))
                f.write("    </TR>")

        f.write("</TABLE>\n")


        ###

        f.write('<A NAME="results_by_parser"></A>\n')
        f.write("<H4>3. Results by Parser</H4>")
        for i, prog in enumerate(prog_names):
            url = programs[prog]["url"]
            f.write("<P>\n")
            f.write('<A NAME="%d"></A>' % i)
            if len(url) > 0:
                f.write('<H4><A HREF="%s">%s</A></H4>\n' % (url, prog))
            else:
                f.write('<H4>%s</H4>\n' % prog)

            ###

            if prog not in status_for_path_for_lib:
                continue
            status_for_path = status_for_path_for_lib[prog]

            paths = list(status_for_path.keys())
            paths.sort()

            f.write('<TABLE>\n')

            f.write("    <TR>\n")
            f.write("        <TH></TH>\n")
            f.write('        <TH class="space"><DIV></DIV></TH>\n')
            f.write("        <TH></TH>\n")
            f.write("    </TR>\n")

            for path in paths:

                f.write("    <TR>\n")
                f.write("        <TD>%s</TD>" % os.path.basename(path))

                status_for_lib = status_for_lib_for_file[path]
                if os.path.exists(path):
                    bytes = open(path, "rb").read()
                else:
                    bytes = [ord(x) for x in "(MISSING FILE)"]

                if prog in status_for_lib:
                    status = status_for_lib[prog]
                    f.write('        <TD class="%s">%s</TD>' % (status, ""))
                else:
                    f.write("        <TD></TD>")
                f.write("        <TD>%s</TD>" % f_underline_non_printable_bytes(bytes))
                f.write("    </TR>")

            f.write('</TABLE>\n')
            f.write("</P>\n")

        ###

        f.write("""

        </BODY>

        </HTML>
        """)
    if os.path.exists('/usr/bin/open'):
        os.system('/usr/bin/open "%s"' % report_path)

###

if __name__ == '__main__':

    restrict_to_path = None
    """
    if len(sys.argv) == 2:
        restrict_to_path = os.path.join(BASE_DIR, sys.argv[1])
        if not os.path.exists(restrict_to_path):
            print("-- file does not exist:", restrict_to_path)
            sys.exit(-1)
    """

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('restrict_to_path', nargs='?', type=str, default=None)
    parser.add_argument('--filter', dest='restrict_to_program', type=argparse.FileType('r'), default=None)

    args = parser.parse_args()

    #args.restrict_to_program = ["C ConcreteServer"]

    run_tests(args.restrict_to_path, args.restrict_to_program)

    generate_report(os.path.join(BASE_DIR, "results/parsing.html"), keep_only_first_result_in_set = False)
    generate_report(os.path.join(BASE_DIR, "results/parsing_pruned.html"), keep_only_first_result_in_set = True)
