#!/bin/sh

# This is a copy of the destroy script from aports-build
# Just running umount -R was not working (stuff simply didnt get unmounted).

set -e

remove=no
case "$1" in
-r | --remove) remove=yes;;
'') ;;
*) echo "Usage: $0 [-r | --remove]"; exit 1;;
esac

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
[ "$(id -u)" -eq 0 ] || _sudo='sudo'

# Unmounts all filesystem under the specified directory tree.
cat /proc/mounts | cut -d' ' -f2 | grep "^$SCRIPT_DIR." | sort -r | while read path; do
echo "Unmounting $path" >&2
$_sudo umount -fn "$path" || exit 1
done

if [ "$remove" = yes ]; then
rm_opts=''
# Just to be extra careful...
rm --help 2>&1 | grep -Fq 'one-file-system' && rm_opts='--one-file-system'

echo "Removing $SCRIPT_DIR" >&2
$_sudo rm -Rf $rm_opts "$SCRIPT_DIR"
else
echo "If you want to remove $SCRIPT_DIR directory, run: $0 --remove" >&2
fi
