#!/bin/bash
#
# A string processing test case copied from bash_completion.

# This function shell-quotes the argument
quote()
{
    local quoted=${1//\'/\'\\\'\'}
    printf "'%s'" "$quoted"
}

# This function shell-dequotes the argument
dequote()
{
    eval printf %s "$1" 2> /dev/null
}

# Helper function for _parse_help and _parse_usage.
__parse_options()
{
    local option option2 i IFS=$' \t\n,/|'

    # Take first found long option, or first one (short) if not found.
    option=
    local -a array
    read -a array <<<"$1"
    for i in "${array[@]}"; do
        case "$i" in
            ---*) break ;;
            --?*) option=$i ; break ;;
            -?*)  [[ $option ]] || option=$i ;;
            *)    break ;;
        esac
    done
    [[ $option ]] || return

    IFS=$' \t\n' # affects parsing of the regexps below...

    # Expand --[no]foo to --foo and --nofoo etc
    if [[ $option =~ (\[((no|dont)-?)\]). ]]; then
        option2=${option/"${BASH_REMATCH[1]}"/}
        option2=${option2%%[<{().[]*}
        printf '%s\n' "${option2/=*/=}"
        option=${option/"${BASH_REMATCH[1]}"/"${BASH_REMATCH[2]}"}
    fi

    option=${option%%[<{().[]*}
    printf '%s\n' "${option/=*/=}"
}

# Parse GNU style help output of the given command.
# @param $1  command; if "-", read from stdin and ignore rest of args
# @param $2  command options (default: --help)
#
_parse_help()
{
    eval local cmd=$( quote "$1" )
    local line
    { case $cmd in
        -) cat ;;
        *) LC_ALL=C "$( dequote "$cmd" )" ${2:---help} 2>&1 ;;
      esac } \
    | while read -r line; do

        [[ $line == *([[:blank:]])-* ]] || continue
        # transform "-f FOO, --foo=FOO" to "-f , --foo=FOO" etc
        while [[ $line =~ \
            ((^|[^-])-[A-Za-z0-9?][[:space:]]+)\[?[A-Z0-9]+\]? ]]; do
            line=${line/"${BASH_REMATCH[0]}"/"${BASH_REMATCH[1]}"}
        done
        __parse_options "${line// or /, }"

    done
}

"$@"

