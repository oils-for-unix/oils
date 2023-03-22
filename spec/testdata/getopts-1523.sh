while getopts abc: opt; do
    case "$opt" in
    [ab])   printf 'opt:%s\n' "$opt";;
    c)  printf 'opt:%s arg:%s\n' "$opt" "$OPTARG";;
    *)  printf 'err:%s\n' "$opt";;
    esac
done
shift $((OPTIND - 1))
[ $# -gt 0 ] && printf 'arg:%s\n' "$@"
