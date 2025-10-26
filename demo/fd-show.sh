# Useful for testing shells
#
# What file descriptor, if any, is open when a sourced file is executing?
#     bash -c '. demo/fd-show.sh'
#     zsh  -c '. demo/fd-show.sh'

ls -l /proc/$$/fd
