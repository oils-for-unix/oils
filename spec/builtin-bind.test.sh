## oils_failures_allowed: 1
## compare_shells: bash

# NB: This is only for NON-interactive tests of bind. 
# See spec/stateful/bind.py for the remaining tests.

#### bind -l should report readline functions

bind -l | sort

## status: 0
## STDOUT:
abort
accept-line
alias-expand-line
arrow-key-prefix
backward-byte
backward-char
backward-delete-char
backward-kill-line
backward-kill-word
backward-word
beginning-of-history
beginning-of-line
bracketed-paste-begin
call-last-kbd-macro
capitalize-word
character-search
character-search-backward
clear-display
clear-screen
complete
complete-command
complete-filename
complete-hostname
complete-into-braces
complete-username
complete-variable
copy-backward-word
copy-forward-word
copy-region-as-kill
dabbrev-expand
delete-char
delete-char-or-list
delete-horizontal-space
digit-argument
display-shell-version
do-lowercase-version
downcase-word
dump-functions
dump-macros
dump-variables
dynamic-complete-history
edit-and-execute-command
emacs-editing-mode
end-kbd-macro
end-of-history
end-of-line
exchange-point-and-mark
fetch-history
forward-backward-delete-char
forward-byte
forward-char
forward-search-history
forward-word
glob-complete-word
glob-expand-word
glob-list-expansions
history-and-alias-expand-line
history-expand-line
history-search-backward
history-search-forward
history-substring-search-backward
history-substring-search-forward
insert-comment
insert-completions
insert-last-argument
kill-line
kill-region
kill-whole-line
kill-word
magic-space
menu-complete
menu-complete-backward
next-history
next-screen-line
non-incremental-forward-search-history
non-incremental-forward-search-history-again
non-incremental-reverse-search-history
non-incremental-reverse-search-history-again
old-menu-complete
operate-and-get-next
overwrite-mode
possible-command-completions
possible-completions
possible-filename-completions
possible-hostname-completions
possible-username-completions
possible-variable-completions
previous-history
previous-screen-line
print-last-kbd-macro
quoted-insert
re-read-init-file
redraw-current-line
reverse-search-history
revert-line
self-insert
set-mark
shell-backward-kill-word
shell-backward-word
shell-expand-line
shell-forward-word
shell-kill-word
shell-transpose-words
skip-csi-sequence
spell-correct-word
start-kbd-macro
tab-insert
tilde-expand
transpose-chars
transpose-words
tty-status
undo
universal-argument
unix-filename-rubout
unix-line-discard
unix-word-rubout
upcase-word
vi-append-eol
vi-append-mode
vi-arg-digit
vi-bWord
vi-back-to-indent
vi-backward-bigword
vi-backward-word
vi-bword
vi-change-case
vi-change-char
vi-change-to
vi-char-search
vi-column
vi-complete
vi-delete
vi-delete-to
vi-eWord
vi-edit-and-execute-command
vi-editing-mode
vi-end-bigword
vi-end-word
vi-eof-maybe
vi-eword
vi-fWord
vi-fetch-history
vi-first-print
vi-forward-bigword
vi-forward-word
vi-fword
vi-goto-mark
vi-insert-beg
vi-insertion-mode
vi-match
vi-movement-mode
vi-next-word
vi-overstrike
vi-overstrike-delete
vi-prev-word
vi-put
vi-redo
vi-replace
vi-rubout
vi-search
vi-search-again
vi-set-mark
vi-subst
vi-tilde-expand
vi-undo
vi-unix-word-rubout
vi-yank-arg
vi-yank-pop
vi-yank-to
yank
yank-last-arg
yank-nth-arg
yank-pop
## END
