/* This module makes GNU readline available to Python.  It has ideas
 * contributed by Lee Busby, LLNL, and William Magro, Cornell Theory
 * Center.  The completer interface was inspired by Lele Gaifax.  More
 * recently, it was largely rewritten by Guido van Rossum.
 */

/* Standard definitions */
#include "Python.h"
#include <setjmp.h>
#include <signal.h>
#include <errno.h>
#include <sys/time.h>

/* ------------------------------------------------------------------------- */

/* OVM_MAIN: This section copied from autotool-generated pyconfig.h. 
 * We're not detecting any of it in Oil's configure script.  They are for
 * ancient readline versions.
 * */

/* Define if you have readline 2.1 */
#define HAVE_RL_CALLBACK 1

/* Define if you can turn off readline's signal handling. */
#define HAVE_RL_CATCH_SIGNAL 1

/* Define if you have readline 2.2 */
#define HAVE_RL_COMPLETION_APPEND_CHARACTER 1

/* Define if you have readline 4.0 */
#define HAVE_RL_COMPLETION_DISPLAY_MATCHES_HOOK 1

/* Define if you have readline 4.2 */
#define HAVE_RL_COMPLETION_MATCHES 1

/* Define if you have rl_completion_suppress_append */
#define HAVE_RL_COMPLETION_SUPPRESS_APPEND 1

/* Define if you have readline 4.0 */
#define HAVE_RL_PRE_INPUT_HOOK 1

/* Define if you have readline 4.0 */
#define HAVE_RL_RESIZE_TERMINAL 1

/* ------------------------------------------------------------------------- */

#if defined(HAVE_SETLOCALE)
/* GNU readline() mistakenly sets the LC_CTYPE locale.
 * This is evil.  Only the user or the app's main() should do this!
 * We must save and restore the locale around the rl_initialize() call.
 */
#define SAVE_LOCALE
#include <locale.h>
#endif

#ifdef SAVE_LOCALE
#  define RESTORE_LOCALE(sl) { setlocale(LC_CTYPE, sl); free(sl); }
#else
#  define RESTORE_LOCALE(sl)
#endif

/* GNU readline definitions */
#undef HAVE_CONFIG_H /* Else readline/chardefs.h includes strings.h */
#include <readline/readline.h>
#include <readline/history.h>

#ifdef HAVE_RL_COMPLETION_MATCHES
#define completion_matches(x, y) \
    rl_completion_matches((x), ((rl_compentry_func_t *)(y)))
#else
#if defined(_RL_FUNCTION_TYPEDEF)
extern char **completion_matches(char *, rl_compentry_func_t *);
#else

#if !defined(__APPLE__)
extern char **completion_matches(char *, CPFunction *);
#endif
#endif
#endif

#ifdef __APPLE__
/*
 * It is possible to link the readline module to the readline
 * emulation library of editline/libedit.
 *
 * On OSX this emulation library is not 100% API compatible
 * with the "real" readline and cannot be detected at compile-time,
 * hence we use a runtime check to detect if we're using libedit
 *
 * Currently there is one known API incompatibility:
 * - 'get_history' has a 1-based index with GNU readline, and a 0-based
 *   index with older versions of libedit's emulation.
 * - Note that replace_history and remove_history use a 0-based index
 *   with both implementations.
 */
static int using_libedit_emulation = 0;
static const char libedit_version_tag[] = "EditLine wrapper";

static int libedit_history_start = 0;
#endif /* __APPLE__ */

#ifdef HAVE_RL_COMPLETION_DISPLAY_MATCHES_HOOK
static void
on_completion_display_matches_hook(char **matches,
                                   int num_matches, int max_length);
#endif

/* Memory allocated for rl_completer_word_break_characters
   (see issue #17289 for the motivation). */
static char *completer_word_break_characters;

/* Exported function to send one line to readline's init file parser */

static PyObject *
parse_and_bind(PyObject *self, PyObject *args)
{
    char *s, *copy;
    int binding_result;

    if (!PyArg_ParseTuple(args, "s:parse_and_bind", &s))
        return NULL;
    /* Make a copy -- rl_parse_and_bind() modifies its argument */
    /* Bernard Herzog */
    copy = malloc(1 + strlen(s));
    if (copy == NULL)
        return PyErr_NoMemory();
    strcpy(copy, s);

    binding_result = rl_parse_and_bind(copy);
    free(copy); /* Free the copy */
    
    if (binding_result != 0) {
        PyErr_Format(PyExc_ValueError, "'%s': invalid binding", s);
        return NULL;
    }

    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_parse_and_bind,
"parse_and_bind(string) -> None\n\
Bind a key sequence to a readline function (or a variable to a value).");



/* Exported function to parse a readline init file */

static PyObject *
read_init_file(PyObject *self, PyObject *args)
{
    char *s = NULL;
    if (!PyArg_ParseTuple(args, "|z:read_init_file", &s))
        return NULL;
    errno = rl_read_init_file(s);
    if (errno)
        return PyErr_SetFromErrno(PyExc_IOError);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_read_init_file,
"read_init_file([filename]) -> None\n\
Execute a readline initialization file.\n\
The default filename is the last filename used.");


/* Exported function to load a readline history file */

static PyObject *
read_history_file(PyObject *self, PyObject *args)
{
    char *s = NULL;
    if (!PyArg_ParseTuple(args, "|z:read_history_file", &s))
        return NULL;
    errno = read_history(s);
    if (errno)
        return PyErr_SetFromErrno(PyExc_IOError);
    Py_RETURN_NONE;
}

static int _history_length = -1; /* do not truncate history by default */
PyDoc_STRVAR(doc_read_history_file,
"read_history_file([filename]) -> None\n\
Load a readline history file.\n\
The default filename is ~/.history.");


/* Exported function to save a readline history file */

static PyObject *
write_history_file(PyObject *self, PyObject *args)
{
    char *s = NULL;
    if (!PyArg_ParseTuple(args, "|z:write_history_file", &s))
        return NULL;
    errno = write_history(s);
    if (!errno && _history_length >= 0)
        history_truncate_file(s, _history_length);
    if (errno)
        return PyErr_SetFromErrno(PyExc_IOError);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_write_history_file,
"write_history_file([filename]) -> None\n\
Save a readline history file.\n\
The default filename is ~/.history.");


/* Set history length */

static PyObject*
set_history_length(PyObject *self, PyObject *args)
{
    int length = _history_length;
    if (!PyArg_ParseTuple(args, "i:set_history_length", &length))
        return NULL;
    _history_length = length;
    Py_RETURN_NONE;
}

PyDoc_STRVAR(set_history_length_doc,
"set_history_length(length) -> None\n\
set the maximal number of lines which will be written to\n\
the history file. A negative length is used to inhibit\n\
history truncation.");


/* Get history length */

static PyObject*
get_history_length(PyObject *self, PyObject *noarg)
{
    return PyInt_FromLong(_history_length);
}

PyDoc_STRVAR(get_history_length_doc,
"get_history_length() -> int\n\
return the maximum number of lines that will be written to\n\
the history file.");


/* Generic hook function setter */

static PyObject *
set_hook(const char *funcname, PyObject **hook_var, PyObject *args)
{
    PyObject *function = Py_None;
    char buf[80];
    PyOS_snprintf(buf, sizeof(buf), "|O:set_%.50s", funcname);
    if (!PyArg_ParseTuple(args, buf, &function))
        return NULL;
    if (function == Py_None) {
        Py_CLEAR(*hook_var);
    }
    else if (PyCallable_Check(function)) {
        PyObject *tmp = *hook_var;
        Py_INCREF(function);
        *hook_var = function;
        Py_XDECREF(tmp);
    }
    else {
        PyOS_snprintf(buf, sizeof(buf),
                      "set_%.50s(func): argument not callable",
                      funcname);
        PyErr_SetString(PyExc_TypeError, buf);
        return NULL;
    }
    Py_RETURN_NONE;
}


/* Exported functions to specify hook functions in Python */

static PyObject *completion_display_matches_hook = NULL;
static PyObject *startup_hook = NULL;
static PyObject *bind_shell_command_hook = NULL;

#ifdef HAVE_RL_PRE_INPUT_HOOK
static PyObject *pre_input_hook = NULL;
#endif

static PyObject *
set_completion_display_matches_hook(PyObject *self, PyObject *args)
{
    PyObject *result = set_hook("completion_display_matches_hook",
                    &completion_display_matches_hook, args);
#ifdef HAVE_RL_COMPLETION_DISPLAY_MATCHES_HOOK
    /* We cannot set this hook globally, since it replaces the
       default completion display. */
    rl_completion_display_matches_hook =
        completion_display_matches_hook ?
#if defined(_RL_FUNCTION_TYPEDEF)
        (rl_compdisp_func_t *)on_completion_display_matches_hook : 0;
#else
        (VFunction *)on_completion_display_matches_hook : 0;
#endif
#endif
    return result;

}

PyDoc_STRVAR(doc_set_completion_display_matches_hook,
"set_completion_display_matches_hook([function]) -> None\n\
Set or remove the completion display function.\n\
The function is called as\n\
  function(substitution, [matches], longest_match_length)\n\
once each time matches need to be displayed.");

static PyObject *
set_startup_hook(PyObject *self, PyObject *args)
{
    return set_hook("startup_hook", &startup_hook, args);
}

PyDoc_STRVAR(doc_set_startup_hook,
"set_startup_hook([function]) -> None\n\
Set or remove the function invoked by the rl_startup_hook callback.\n\
The function is called with no arguments just\n\
before readline prints the first prompt.");


#ifdef HAVE_RL_PRE_INPUT_HOOK

/* Set pre-input hook */

static PyObject *
set_pre_input_hook(PyObject *self, PyObject *args)
{
    return set_hook("pre_input_hook", &pre_input_hook, args);
}

PyDoc_STRVAR(doc_set_pre_input_hook,
"set_pre_input_hook([function]) -> None\n\
Set or remove the function invoked by the rl_pre_input_hook callback.\n\
The function is called with no arguments after the first prompt\n\
has been printed and just before readline starts reading input\n\
characters.");

#endif


/* Exported function to specify a word completer in Python */

static PyObject *completer = NULL;

static PyObject *begidx = NULL;
static PyObject *endidx = NULL;


/* Get the completion type for the scope of the tab-completion */
static PyObject *
get_completion_type(PyObject *self, PyObject *noarg)
{
  return PyInt_FromLong(rl_completion_type);
}

PyDoc_STRVAR(doc_get_completion_type,
"get_completion_type() -> int\n\
Get the type of completion being attempted.");


/* Set bind -x Python command hook */

static PyObject *
set_bind_shell_command_hook(PyObject *self, PyObject *args)
{
    return set_hook("bind_shell_command_hook", &bind_shell_command_hook, args);
}

PyDoc_STRVAR(doc_set_bind_shell_command_hook,
"set_bind_shell_command_hook([function]) -> None\n\
Set or remove the function invoked by the rl_bind_keyseq_in_map callback.\n\
The function is called with three arguments: the string to parse and evaluate,\n\
the contents of the readline buffer to put in the READLINE_LINE env var,\n\
and the int of the cursor's point in the buffer to put in READLINE_POINT.\n\
It must return the READLINE_* vars in a tuple.");


/* Get the beginning index for the scope of the tab-completion */

static PyObject *
get_begidx(PyObject *self, PyObject *noarg)
{
    Py_INCREF(begidx);
    return begidx;
}

PyDoc_STRVAR(doc_get_begidx,
"get_begidx() -> int\n\
get the beginning index of the completion scope");


/* Get the ending index for the scope of the tab-completion */

static PyObject *
get_endidx(PyObject *self, PyObject *noarg)
{
    Py_INCREF(endidx);
    return endidx;
}

PyDoc_STRVAR(doc_get_endidx,
"get_endidx() -> int\n\
get the ending index of the completion scope");


/* Set the tab-completion word-delimiters that readline uses */

static PyObject *
set_completer_delims(PyObject *self, PyObject *args)
{
    char *break_chars;

    if (!PyArg_ParseTuple(args, "s:set_completer_delims", &break_chars)) {
        return NULL;
    }
    /* Keep a reference to the allocated memory in the module state in case
       some other module modifies rl_completer_word_break_characters
       (see issue #17289). */
    break_chars = strdup(break_chars);
    if (break_chars) {
        free(completer_word_break_characters);
        completer_word_break_characters = break_chars;
        rl_completer_word_break_characters = break_chars;
        Py_RETURN_NONE;
    }
    else
        return PyErr_NoMemory();
}

PyDoc_STRVAR(doc_set_completer_delims,
"set_completer_delims(string) -> None\n\
set the word delimiters for completion");

/* _py_free_history_entry: Utility function to free a history entry. */

#if defined(RL_READLINE_VERSION) && RL_READLINE_VERSION >= 0x0500

/* Readline version >= 5.0 introduced a timestamp field into the history entry
   structure; this needs to be freed to avoid a memory leak.  This version of
   readline also introduced the handy 'free_history_entry' function, which
   takes care of the timestamp. */

static void
_py_free_history_entry(HIST_ENTRY *entry)
{
    histdata_t data = free_history_entry(entry);
    free(data);
}

#else

/* No free_history_entry function;  free everything manually. */

static void
_py_free_history_entry(HIST_ENTRY *entry)
{
    if (entry->line)
        free((void *)entry->line);
    if (entry->data)
        free(entry->data);
    free(entry);
}

#endif

static PyObject *
py_remove_history(PyObject *self, PyObject *args)
{
    int entry_number;
    HIST_ENTRY *entry;

    if (!PyArg_ParseTuple(args, "i:remove_history_item", &entry_number))
        return NULL;
    if (entry_number < 0) {
        PyErr_SetString(PyExc_ValueError,
                        "History index cannot be negative");
        return NULL;
    }
    entry = remove_history(entry_number);
    if (!entry) {
        PyErr_Format(PyExc_ValueError,
                     "No history item at position %d",
                      entry_number);
        return NULL;
    }
    /* free memory allocated for the history entry */
    _py_free_history_entry(entry);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_remove_history,
"remove_history_item(pos) -> None\n\
remove history item given by its position");

static PyObject *
py_replace_history(PyObject *self, PyObject *args)
{
    int entry_number;
    char *line;
    HIST_ENTRY *old_entry;

    if (!PyArg_ParseTuple(args, "is:replace_history_item", &entry_number,
                          &line)) {
        return NULL;
    }
    if (entry_number < 0) {
        PyErr_SetString(PyExc_ValueError,
                        "History index cannot be negative");
        return NULL;
    }
    old_entry = replace_history_entry(entry_number, line, (void *)NULL);
    if (!old_entry) {
        PyErr_Format(PyExc_ValueError,
                     "No history item at position %d",
                     entry_number);
        return NULL;
    }
    /* free memory allocated for the old history entry */
    _py_free_history_entry(old_entry);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_replace_history,
"replace_history_item(pos, line) -> None\n\
replaces history item given by its position with contents of line");

/* Add a line to the history buffer */

static PyObject *
py_add_history(PyObject *self, PyObject *args)
{
    char *line;

    if(!PyArg_ParseTuple(args, "s:add_history", &line)) {
        return NULL;
    }
    add_history(line);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_add_history,
"add_history(string) -> None\n\
add an item to the history buffer");


/* Get the tab-completion word-delimiters that readline uses */

static PyObject *
get_completer_delims(PyObject *self, PyObject *noarg)
{
    return PyString_FromString(rl_completer_word_break_characters);
}

PyDoc_STRVAR(doc_get_completer_delims,
"get_completer_delims() -> string\n\
get the word delimiters for completion");


/* Set the completer function */

static PyObject *
set_completer(PyObject *self, PyObject *args)
{
    return set_hook("completer", &completer, args);
}

PyDoc_STRVAR(doc_set_completer,
"set_completer([function]) -> None\n\
Set or remove the completer function.\n\
The function is called as function(text, state),\n\
for state in 0, 1, 2, ..., until it returns a non-string.\n\
It should return the next possible completion starting with 'text'.");


static PyObject *
get_completer(PyObject *self, PyObject *noargs)
{
    if (completer == NULL) {
        Py_RETURN_NONE;
    }
    Py_INCREF(completer);
    return completer;
}

PyDoc_STRVAR(doc_get_completer,
"get_completer() -> function\n\
\n\
Returns current completer function.");

/* Private function to get current length of history.  XXX It may be
 * possible to replace this with a direct use of history_length instead,
 * but it's not clear whether BSD's libedit keeps history_length up to date.
 * See issue #8065.*/

static int
_py_get_history_length(void)
{
    HISTORY_STATE *hist_st = history_get_history_state();
    int length = hist_st->length;
    /* the history docs don't say so, but the address of hist_st changes each
       time history_get_history_state is called which makes me think it's
       freshly malloc'd memory...  on the other hand, the address of the last
       line stays the same as long as history isn't extended, so it appears to
       be malloc'd but managed by the history package... */
    free(hist_st);
    return length;
}

/* Exported function to get any element of history */

static PyObject *
get_history_item(PyObject *self, PyObject *args)
{
    int idx = 0;
    HIST_ENTRY *hist_ent;

    if (!PyArg_ParseTuple(args, "i:get_history_item", &idx))
        return NULL;
#ifdef  __APPLE__
    if (using_libedit_emulation) {
        /* Older versions of libedit's readline emulation
         * use 0-based indexes, while readline and newer
         * versions of libedit use 1-based indexes.
         */
        int length = _py_get_history_length();

        idx = idx - 1 + libedit_history_start;

        /*
         * Apple's readline emulation crashes when
         * the index is out of range, therefore
         * test for that and fail gracefully.
         */
        if (idx < (0 + libedit_history_start)
                || idx >= (length + libedit_history_start)) {
            Py_RETURN_NONE;
        }
    }
#endif /* __APPLE__ */
    if ((hist_ent = history_get(idx)))
        return PyString_FromString(hist_ent->line);
    else {
        Py_RETURN_NONE;
    }
}

PyDoc_STRVAR(doc_get_history_item,
"get_history_item() -> string\n\
return the current contents of history item at index.");


/* Exported function to get current length of history */

static PyObject *
get_current_history_length(PyObject *self, PyObject *noarg)
{
    return PyInt_FromLong((long)_py_get_history_length());
}

PyDoc_STRVAR(doc_get_current_history_length,
"get_current_history_length() -> integer\n\
return the current (not the maximum) length of history.");


/* Exported function to read the current line buffer */

static PyObject *
get_line_buffer(PyObject *self, PyObject *noarg)
{
    return PyString_FromString(rl_line_buffer);
}

PyDoc_STRVAR(doc_get_line_buffer,
"get_line_buffer() -> string\n\
return the current contents of the line buffer.");


#ifdef HAVE_RL_COMPLETION_APPEND_CHARACTER

/* Exported function to clear the current history */

static PyObject *
py_clear_history(PyObject *self, PyObject *noarg)
{
    clear_history();
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_clear_history,
"clear_history() -> None\n\
Clear the current readline history.");
#endif

/* Added for OSH.  We need to call this in our SIGWINCH handler so global
 * variables in readline get updated. */
static PyObject *
py_resize_terminal(PyObject *self, PyObject *noarg)
{
    rl_resize_terminal();
    Py_RETURN_NONE;
}

/* Exported function to insert text into the line buffer */

static PyObject *
insert_text(PyObject *self, PyObject *args)
{
    char *s;
    if (!PyArg_ParseTuple(args, "s:insert_text", &s))
        return NULL;
    rl_insert_text(s);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_insert_text,
"insert_text(string) -> None\n\
Insert text into the line buffer at the cursor position.");


/* Redisplay the line buffer */

static PyObject *
redisplay(PyObject *self, PyObject *noarg)
{
    rl_redisplay();
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_redisplay,
"redisplay() -> None\n\
Change what's displayed on the screen to reflect the current\n\
contents of the line buffer.");


/* Functions added to implement the 'bind' builtin in OSH */

/* -x/-X command keymaps */
static Keymap emacs_cmd_map;
static Keymap vi_insert_cmd_map;
static Keymap vi_movement_cmd_map;

/* 
    These forcibly cast between a Keymap* and a rl_command_func_t*. Readline 
    uses an additional `.type` field to keep track of the pointer's true type. 
*/
#define RL_KEYMAP_TO_FUNCTION(data) (rl_command_func_t *)(data)
#define RL_FUNCTION_TO_KEYMAP(map, key) (Keymap)(map[key].function)

static void
_init_command_maps(void)
{
    emacs_cmd_map = rl_make_bare_keymap();
    vi_insert_cmd_map = rl_make_bare_keymap();
    vi_movement_cmd_map = rl_make_bare_keymap();

    /* Ensure that Esc- and Ctrl-X are also keymaps */
    emacs_cmd_map[CTRL('X')].type = ISKMAP;
    emacs_cmd_map[CTRL('X')].function = RL_KEYMAP_TO_FUNCTION(rl_make_bare_keymap());
    emacs_cmd_map[ESC].type = ISKMAP;
    emacs_cmd_map[ESC].function = RL_KEYMAP_TO_FUNCTION(rl_make_bare_keymap());
}

static Keymap
_get_associated_cmd_map(Keymap kmap)
{
    if (emacs_cmd_map == NULL)
        _init_command_maps();

    if (kmap == emacs_standard_keymap)
        return emacs_cmd_map;
    else if (kmap == vi_insertion_keymap)
        return vi_insert_cmd_map;
    else if (kmap == vi_movement_keymap)
        return vi_movement_cmd_map;
    else if (kmap == emacs_meta_keymap)
        return (RL_FUNCTION_TO_KEYMAP(emacs_cmd_map, ESC));
    else if (kmap == emacs_ctlx_keymap)
        return (RL_FUNCTION_TO_KEYMAP(emacs_cmd_map, CTRL('X')));

    return (Keymap) NULL;
}

/* List binding functions */
static PyObject*
list_funmap_names(PyObject *self, PyObject *args)
{
    rl_list_funmap_names();
    // printf ("Compiled w/ readline version: %s\n", rl_library_version ? rl_library_version : "unknown");
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_list_funmap_names,
"list_funmap_names() -> None\n\
Print all of the available readline functions.");

/* Print readline functions and their bindings */

static PyObject*
function_dumper(PyObject *self, PyObject *args)
{
    int print_readably;

    if (!PyArg_ParseTuple(args, "i:function_dumper", &print_readably))
        return NULL;

    rl_function_dumper(print_readably);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_list_function_dumper,
"function_dumper(bool) -> None\n\
Print all readline functions and their bindings.");

/* Print macros, their bindings, and their string outputs */

static PyObject*
macro_dumper(PyObject *self, PyObject *args)
{
    int print_readably;

    if (!PyArg_ParseTuple(args, "i:macro_dumper", &print_readably))
        return NULL;

    rl_macro_dumper(print_readably);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_list_macro_dumper,
"macro_dumper(bool) -> None\n\
Print all readline sequences bound to macros and the strings they output.");

/* List readline variables */

static PyObject*
variable_dumper(PyObject *self, PyObject *args)
{
    int print_readably;

    if (!PyArg_ParseTuple(args, "i:variable_dumper", &print_readably))
        return NULL;

    rl_variable_dumper(print_readably);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_list_variable_dumper,
"variable_dumper(bool) -> None\n\
List readline variables and their values.");


/* Query bindings for a function name */

// readline returns null-terminated string arrays
void _strvec_dispose(char **strvec) {
    register int i;

    if (strvec == NULL)
        return;
    
    for (i = 0; strvec[i]; i++) {
        free(strvec[i]);
    }
    
    free(strvec);
}

// Nicely prints a strvec with commas and an and
// like '"foo", "bar", and "moop"'
void _pprint_strvec_list(char **strvec) {
    int i;

    for (i = 0; strvec[i]; i++) {
        printf("\"%s\"", strvec[i]);
        if (strvec[i + 1]) {
            printf(", ");
            if (!strvec[i + 2])
                printf("and ");
        }
    }
}

/* 
NB: readline (and bash) have a bug where they don't see certain keyseqs, even
if the bindings work. E.g., if you bind a number key like "\C-7", it will be
bound, but reporting code like query_bindings and function_dumper won't count it.
*/

static PyObject* 
query_bindings(PyObject *self, PyObject *args)
{
    char *fn_name;
    rl_command_func_t *cmd_fn;
    char **key_seqs;

    if (!PyArg_ParseTuple(args, "s:query_bindings", &fn_name))
        return NULL;

    cmd_fn = rl_named_function(fn_name);

    if (cmd_fn == NULL) {
        PyErr_Format(PyExc_ValueError, "`%s': unknown function name", fn_name);
        return NULL;
    }

    key_seqs = rl_invoking_keyseqs(cmd_fn);

    if (!key_seqs) {
        // print to stdout, but return an error
        printf("%s is not bound to any keys.\n", fn_name); 
        PyErr_SetNone(PyExc_ValueError);
        return NULL;
    }

    printf("%s can be invoked via ", fn_name);
    _pprint_strvec_list(key_seqs);
    printf(".\n");

    _strvec_dispose(key_seqs);
    
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_query_bindings,
"query_bindings(str) -> None\n\
Query bindings to see what's bound to a given function.");


static PyObject*
unbind_rl_function(PyObject *self, PyObject *args)
{
    char *fn_name;
    rl_command_func_t *cmd_fn;

    if (!PyArg_ParseTuple(args, "s:unbind_rl_function", &fn_name))
        return NULL;

    cmd_fn = rl_named_function(fn_name);
    if (cmd_fn == NULL) {
        PyErr_Format(PyExc_ValueError, "`%s': unknown function name", fn_name);
        return NULL;
    }

    rl_unbind_function_in_map(cmd_fn, rl_get_keymap());
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_unbind_rl_function,
"unbind_rl_function(function_name) -> None\n\
Unbind all keys bound to the named readline function in the current keymap.");


static PyObject*
unbind_shell_cmd(PyObject *self, PyObject *args)
{
    char *keyseq;
    Keymap cmd_map;

    if (!PyArg_ParseTuple(args, "s:unbind_shell_cmd", &keyseq))
        return NULL;

    cmd_map = _get_associated_cmd_map(rl_get_keymap());
    if (cmd_map == NULL) {
        PyErr_SetString(PyExc_ValueError, "Could not get command map for current keymap");
        return NULL;
    }

    if (rl_bind_keyseq_in_map(keyseq, (rl_command_func_t *)NULL, cmd_map) != 0) {
        PyErr_Format(PyExc_ValueError, "'%s': can't unbind from shell command keymap", keyseq);
        return NULL;
    }

    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_unbind_shell_cmd,
"unbind_shell_cmd(key_sequence) -> None\n\
Unbind a key sequence from the current keymap's associated shell command map.");


static PyObject*
print_shell_cmd_map(PyObject *self, PyObject *noarg)
{
    Keymap curr_map, cmd_map;

    curr_map = rl_get_keymap();
    cmd_map = _get_associated_cmd_map(curr_map);
    
    if (cmd_map == NULL) {
        PyErr_SetString(PyExc_ValueError, "Could not get shell command map for current keymap");
        return NULL;
    }

    rl_set_keymap(cmd_map);
    rl_macro_dumper(1); 
    rl_set_keymap(curr_map);

    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_print_shell_cmd_map,
"print_shell_cmd_map() -> None\n\
Print all bindings for shell commands in the current keymap.");


/* Remove all bindings for a given keyseq */

static PyObject*
unbind_keyseq(PyObject *self, PyObject *args)
{
    char *seq, *keyseq;
    int kslen, type;
    rl_command_func_t *fn;

    if (!PyArg_ParseTuple(args, "s:unbind_keyseq", &seq))
        return NULL;

    // Commented code below based on bash 5.x unbinding code, which fails on 
    // readline versions before 2019.

    // keyseq = (char *)malloc((2 * strlen(seq)) + 1);
    // if (rl_translate_keyseq(seq, keyseq, &kslen) != 0) {
    //     free(keyseq);
    //     PyErr_Format(PyExc_ValueError, "'%s': cannot translate key sequence", seq);
    //     return NULL;
    // }

    // fn = rl_function_of_keyseq_len(keyseq, kslen, (Keymap)NULL, &type);
    // if (!fn) {
    //     free(keyseq);
    //     Py_RETURN_NONE;
    // }

    // if (type == ISKMAP) {
    //     fn = ((Keymap)fn)[ANYOTHERKEY].function;
    // }

    // if (rl_bind_keyseq(seq, (rl_command_func_t *)NULL) != 0) {
    //     free(keyseq);
    //     PyErr_Format(PyExc_ValueError, "'%s': cannot unbind", seq);
    //     return NULL;
    // }

    // /* 
    // TODO: Handle shell command unbinding if f == bash_execute_unix_command or
    // rather, whatever the osh equivalent will be
    // */

    // free(keyseq);
    // Py_RETURN_NONE;

    // End bash 5.x unbinding code



    // Code below based on bash 4 unbinding code from 2011

    if (rl_bind_keyseq (seq, (rl_command_func_t *)NULL) != 0) {
        PyErr_Format(PyExc_ValueError, "'%s': cannot unbind", seq);
        return NULL;
    }

    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_unbind_keyseq,
"unbind_keyseq(sequence) -> None\n\
Unbind a key sequence from the current keymap.");


/* Support fns for bind -x */

static void 
debug_print(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    printf("[osh_execute] ");
    vprintf(fmt, args);
    printf("\n");
    va_end(args);
}

static void 
make_line_if_needed(char *new_line)
{
    if (strcmp(new_line, rl_line_buffer) != 0) {
        rl_point = rl_end;

        rl_add_undo(UNDO_BEGIN, 0, 0, 0);
        rl_delete_text(0, rl_point);
        rl_point = rl_end = rl_mark = 0;
        rl_insert_text(new_line);
        rl_add_undo(UNDO_END, 0, 0, 0);
    }
}

static char*
get_bound_command(Keymap cmd_map) {
    int type;
    char *cmd = (char *)rl_function_of_keyseq(rl_executing_keyseq, cmd_map, &type);
    
    if (cmd == NULL || type != ISMACR) {
        PyErr_SetString(PyExc_RuntimeError, 
            "Cannot find shell command bound to this key sequence");
        return NULL;
    }
    
    // debug_print("Found bound command: '%s'", cmd);
    return cmd;
}

static void
clear_current_line(int use_ce) {
    if (use_ce) {
        // debug_print("Clearing line with termcap 'ce'");
        rl_clear_visible_line();
        fflush(rl_outstream);
    } else {
        // debug_print("No termcap 'ce', using newline");
        rl_crlf();
    }
}


#if 0
/* Save readline state to Python variables */
static int
save_readline_state(void) {
    PyObject *line = NULL, *point = NULL;
    
    debug_print("Saving readline state - line: '%s', point: %d", 
                rl_line_buffer, rl_point);

    /* Create Python string for readline line */
    line = PyString_FromString(rl_line_buffer);
    if (!line) {
        PyErr_SetString(PyExc_RuntimeError, 
            "Failed to convert readline line to Python string");
        return 0;
    }

    /* Create Python int for readline point */
    point = PyInt_FromLong(rl_point);
    if (!point) {
        Py_DECREF(line);
        PyErr_SetString(PyExc_RuntimeError,
            "Failed to convert readline point to Python int"); 
        return 0;
    }

    /* Set the Python variables */
    if (PyDict_SetItemString(PyEval_GetGlobals(), "READLINE_LINE", line) < 0 ||
        PyDict_SetItemString(PyEval_GetGlobals(), "READLINE_POINT", point) < 0) {
        Py_DECREF(line);
        Py_DECREF(point);
        PyErr_SetString(PyExc_RuntimeError,
            "Failed to set READLINE_LINE/POINT variables");
        return 0;
    }

    Py_DECREF(line);
    Py_DECREF(point);
    return 1;
}

/* Update readline state from Python variables */
static int 
restore_readline_state(void) {
    PyObject *line = NULL, *point = NULL;
    const char *new_line;
    long new_point;

    debug_print("Restoring readline state from Python variables");

    /* Get the Python variables */
    line = PyDict_GetItemString(PyEval_GetGlobals(), "READLINE_LINE");
    point = PyDict_GetItemString(PyEval_GetGlobals(), "READLINE_POINT");

    if (line && PyString_Check(line)) {
        new_line = PyString_AsString(line);
        debug_print("Got new line from Python: '%s'", new_line);
        
        /* Update if different */
        if (strcmp(new_line, rl_line_buffer) != 0) {
            debug_print("Line changed, updating readline buffer");
            make_line_if_needed((char *)new_line);
        }
    }

    if (point && PyInt_Check(point)) {
        new_point = PyInt_AsLong(point);
        debug_print("Got new point from Python: %ld", new_point);
        
        /* Validate and update point if needed */
        if (new_point != rl_point) {
            if (new_point > rl_end)
                new_point = rl_end;
            else if (new_point < 0) 
                new_point = 0;
            
            debug_print("Point changed, updating to: %ld", new_point);
            rl_point = new_point;
        }
    }

    return 1;
}
#endif


/* Main entry point for executing shell commands. Based on bash_execute_unix_command */

static int
on_bind_shell_command_hook(int count /* unused */, int key /* unused */) {
    char *cmd;
    int use_ce;
    Keymap cmd_map;
    PyObject *r = NULL;
    #ifdef WITH_THREAD
        PyGILState_STATE gilstate;
    #endif
    int cmd_return_code;
    char *line_buffer;
    char *point;
    int result;

    debug_print("Starting shell command execution");

#ifdef WITH_THREAD
    gilstate = PyGILState_Ensure();
#endif

    if (bind_shell_command_hook == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "No bind_shell_command_hook set");
        return 1;
    }

    cmd_map = _get_associated_cmd_map(rl_get_keymap());
    cmd = get_bound_command(cmd_map);
    if (!cmd) { 
        PyErr_SetString(PyExc_RuntimeError, "on_bind_shell_command_hook: Cannot find shell command in keymap");
        rl_crlf();
        rl_forced_update_display();
        return 1;
    }

    use_ce = rl_get_termcap("ce") != NULL;
    clear_current_line(use_ce);

    // debug_print("Preparing to execute shell command: '%s'", cmd);
    // debug_print("rl_line_buffer: '%s'", rl_line_buffer);
    // debug_print("rl_point: '%i'", rl_point);

    r = PyObject_CallFunction(bind_shell_command_hook,
                            "ssi", cmd, rl_line_buffer, rl_point);
    if (r == NULL) {
        PyErr_Print();
        result = 1;
        goto cleanup;
    }
    if (!PyArg_ParseTuple(r, "iss", &cmd_return_code, &line_buffer, &point)) {
        PyErr_SetString(PyExc_ValueError, "Expected (int, str, str) tuple from bind_shell_command_hook");
        result = 1;
        goto cleanup;
    }

    // debug_print("Command return code: %d", cmd_return_code);
    // debug_print("New line buffer: '%s'", line_buffer);
    // debug_print("New point: '%s'", point);

    // if (save_readline_state() != 1 || restore_readline_state() != 1) {
    //     PyErr_SetString(PyExc_RuntimeError, "Failed to update readline state");
    //     result = 1;
    //     goto cleanup;
    // }


    /* Redraw the prompt */
    if (use_ce) // need to handle a  `&& return code != 124` somehow
        rl_redraw_prompt_last_line();
    else
        rl_forced_update_display();

    result = 0; 
    // debug_print("Completed shell command execution");

cleanup:
    Py_XDECREF(r);
#ifdef WITH_THREAD
    PyGILState_Release(gilstate);
#endif

done:
    return result;
}


/* Binds a key sequence to arbitrary shell code, not readline fns */
static PyObject*
bind_shell_command(PyObject *self, PyObject *args) {
    const char *kseq;
    const char *cmd, *cparam;
    Keymap kmap, cmd_xmap;

    if (!PyArg_ParseTuple(args, "ss:bind_shell_command", &kseq, &cparam)) {
        return NULL;
    }

    /* readline will own the cmd string, so we need to make a copy */
    cmd = strdup(cparam);
    if (cmd == NULL) {
        return PyErr_NoMemory();
    }

    kmap = rl_get_keymap();
    cmd_xmap = _get_associated_cmd_map(kmap);

    
    if (rl_generic_bind(ISMACR, kseq, (char *)cmd, cmd_xmap) != 0 
        || rl_bind_keyseq_in_map (kseq, on_bind_shell_command_hook, kmap) != 0) {
        PyErr_Format(PyExc_RuntimeError, "Failed to bind key sequence '%s' to command '%s'", kseq, cmd);
        free(cmd);
        return NULL;
    }

    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_bind_shell_command,
"bind_shell_command(key_sequence, command) -> None\n\
Bind a key sequence to a shell command in the current keymap.");


/* Keymap toggling code */
static Keymap orig_keymap = NULL;

static PyObject*
use_temp_keymap(PyObject *self, PyObject *args)
{
    char *keymap_name;
    Keymap new_keymap;

    if (!PyArg_ParseTuple(args, "s:use_temp_keymap", &keymap_name))
        return NULL;

    new_keymap = rl_get_keymap_by_name(keymap_name);
    if (new_keymap == NULL) {
        PyErr_Format(PyExc_ValueError, "`%s': unknown keymap name", keymap_name);
        return NULL;
    }

    orig_keymap = rl_get_keymap();
    rl_set_keymap(new_keymap);
    
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_use_temp_keymap,
"use_temp_keymap(keymap_name) -> None\n\
Temporarily switch to named keymap, saving the current one.");

static PyObject*
restore_orig_keymap(PyObject *self, PyObject *args)
{
    if (orig_keymap != NULL) {
        rl_set_keymap(orig_keymap);
        orig_keymap = NULL;
    }
    
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_restore_orig_keymap,
"restore_orig_keymap() -> None\n\
Restore the previously saved keymap if one exists.");

/* Table of functions exported by the module */

static struct PyMethodDef readline_methods[] = {
    {"parse_and_bind", parse_and_bind, METH_VARARGS, doc_parse_and_bind},
    {"get_line_buffer", get_line_buffer, METH_NOARGS, doc_get_line_buffer},
    {"insert_text", insert_text, METH_VARARGS, doc_insert_text},
    {"redisplay", redisplay, METH_NOARGS, doc_redisplay},
    {"read_init_file", read_init_file, METH_VARARGS, doc_read_init_file},
    {"read_history_file", read_history_file,
     METH_VARARGS, doc_read_history_file},
    {"write_history_file", write_history_file,
     METH_VARARGS, doc_write_history_file},
    {"get_history_item", get_history_item,
     METH_VARARGS, doc_get_history_item},
    {"get_current_history_length", (PyCFunction)get_current_history_length,
     METH_NOARGS, doc_get_current_history_length},
    {"set_history_length", set_history_length,
     METH_VARARGS, set_history_length_doc},
    {"get_history_length", get_history_length,
     METH_NOARGS, get_history_length_doc},
    {"set_completer", set_completer, METH_VARARGS, doc_set_completer},
    {"get_completer", get_completer, METH_NOARGS, doc_get_completer},
    {"get_completion_type", get_completion_type,
     METH_NOARGS, doc_get_completion_type},
    {"get_begidx", get_begidx, METH_NOARGS, doc_get_begidx},
    {"get_endidx", get_endidx, METH_NOARGS, doc_get_endidx},

    {"set_completer_delims", set_completer_delims,
     METH_VARARGS, doc_set_completer_delims},
    {"add_history", py_add_history, METH_VARARGS, doc_add_history},
    {"remove_history_item", py_remove_history, METH_VARARGS, doc_remove_history},
    {"replace_history_item", py_replace_history, METH_VARARGS, doc_replace_history},
    {"get_completer_delims", get_completer_delims,
     METH_NOARGS, doc_get_completer_delims},

    {"set_completion_display_matches_hook", set_completion_display_matches_hook,
     METH_VARARGS, doc_set_completion_display_matches_hook},
    {"set_startup_hook", set_startup_hook,
     METH_VARARGS, doc_set_startup_hook},
    {"set_pre_input_hook", set_pre_input_hook,
     METH_VARARGS, doc_set_pre_input_hook},
    {"clear_history", py_clear_history, METH_NOARGS, doc_clear_history},
    {"resize_terminal", py_resize_terminal, METH_NOARGS, ""},

    /* Functions added to implement the 'bind' builtin in OSH */
    {"list_funmap_names", list_funmap_names, METH_NOARGS, doc_list_funmap_names},
    {"function_dumper", function_dumper, METH_VARARGS, doc_list_function_dumper},
    {"macro_dumper", macro_dumper, METH_VARARGS, doc_list_macro_dumper},
    {"variable_dumper", variable_dumper, METH_VARARGS, doc_list_variable_dumper},
    {"query_bindings", query_bindings, METH_VARARGS, doc_query_bindings},
    {"unbind_rl_function", unbind_rl_function, METH_VARARGS, doc_unbind_rl_function},
    {"use_temp_keymap", use_temp_keymap, METH_VARARGS, doc_use_temp_keymap},
    {"restore_orig_keymap", restore_orig_keymap, METH_NOARGS, doc_restore_orig_keymap},
    {"unbind_shell_cmd", unbind_shell_cmd, METH_VARARGS, doc_unbind_shell_cmd},
    {"print_shell_cmd_map", print_shell_cmd_map, METH_NOARGS, doc_print_shell_cmd_map},
    {"unbind_keyseq", unbind_keyseq, METH_VARARGS, doc_unbind_keyseq},
    {"bind_shell_command", bind_shell_command, METH_VARARGS, doc_bind_shell_command},
    {"set_bind_shell_command_hook", set_bind_shell_command_hook,
     METH_VARARGS, doc_set_bind_shell_command_hook},
    {0, 0}
};


/* C function to call the Python hooks. */

static int
on_hook(PyObject *func)
{
    int result = 0;
    if (func != NULL) {
        PyObject *r;
#ifdef WITH_THREAD
        PyGILState_STATE gilstate = PyGILState_Ensure();
#endif
        r = PyObject_CallFunction(func, NULL);
        if (r == NULL)
            goto error;
        if (r == Py_None)
            result = 0;
        else {
            result = PyInt_AsLong(r);
            if (result == -1 && PyErr_Occurred())
                goto error;
        }
        Py_DECREF(r);
        goto done;
      error:
        PyErr_Clear();
        Py_XDECREF(r);
      done:
#ifdef WITH_THREAD
        PyGILState_Release(gilstate);
#endif
        return result;
    }
    return result;
}

static int
#if defined(_RL_FUNCTION_TYPEDEF)
on_startup_hook(void)
#else
on_startup_hook()
#endif
{
    return on_hook(startup_hook);
}

#ifdef HAVE_RL_PRE_INPUT_HOOK
static int
#if defined(_RL_FUNCTION_TYPEDEF)
on_pre_input_hook(void)
#else
on_pre_input_hook()
#endif
{
    return on_hook(pre_input_hook);
}
#endif


/* C function to call the Python completion_display_matches */

#ifdef HAVE_RL_COMPLETION_DISPLAY_MATCHES_HOOK
static void
on_completion_display_matches_hook(char **matches,
                                   int num_matches, int max_length)
{
    int i;
    PyObject *m=NULL, *s=NULL, *r=NULL;
#ifdef WITH_THREAD
    PyGILState_STATE gilstate = PyGILState_Ensure();
#endif
    m = PyList_New(num_matches);
    if (m == NULL)
        goto error;
    for (i = 0; i < num_matches; i++) {
        s = PyString_FromString(matches[i+1]);
        if (s == NULL)
            goto error;
        if (PyList_SetItem(m, i, s) == -1)
            goto error;
    }

    r = PyObject_CallFunction(completion_display_matches_hook,
                              "sOi", matches[0], m, max_length);

    Py_DECREF(m); m=NULL;

    if (r == NULL ||
        (r != Py_None && PyInt_AsLong(r) == -1 && PyErr_Occurred())) {
        goto error;
    }
    Py_XDECREF(r); r=NULL;

    if (0) {
    error:
        PyErr_Clear();
        Py_XDECREF(m);
        Py_XDECREF(r);
    }
#ifdef WITH_THREAD
    PyGILState_Release(gilstate);
#endif
}

#endif

#ifdef HAVE_RL_RESIZE_TERMINAL
static volatile sig_atomic_t sigwinch_received;
static PyOS_sighandler_t sigwinch_ohandler;

static void
readline_sigwinch_handler(int signum)
{
    sigwinch_received = 1;
    if (sigwinch_ohandler &&
            sigwinch_ohandler != SIG_IGN && sigwinch_ohandler != SIG_DFL)
        sigwinch_ohandler(signum);
}
#endif

/* C function to call the Python completer. */

static char *
on_completion(const char *text, int state)
{
    char *result = NULL;
    if (completer != NULL) {
        PyObject *r;
#ifdef WITH_THREAD
        PyGILState_STATE gilstate = PyGILState_Ensure();
#endif
        rl_attempted_completion_over = 1;
        r = PyObject_CallFunction(completer, "si", text, state);
        if (r == NULL)
            goto error;
        if (r == Py_None) {
            result = NULL;
        }
        else {
            char *s = PyString_AsString(r);
            if (s == NULL)
                goto error;
            result = strdup(s);
        }
        Py_DECREF(r);
        goto done;
      error:
        PyErr_Clear();
        Py_XDECREF(r);
      done:
#ifdef WITH_THREAD
        PyGILState_Release(gilstate);
#endif
        return result;
    }
    return result;
}


/* A more flexible constructor that saves the "begidx" and "endidx"
 * before calling the normal completer */

static char **
flex_complete(const char *text, int start, int end)
{
#ifdef HAVE_RL_COMPLETION_APPEND_CHARACTER
    rl_completion_append_character ='\0';
#endif
#ifdef HAVE_RL_COMPLETION_SUPPRESS_APPEND
    rl_completion_suppress_append = 0;
#endif
    Py_XDECREF(begidx);
    Py_XDECREF(endidx);
    begidx = PyInt_FromLong((long) start);
    endidx = PyInt_FromLong((long) end);
    return completion_matches(text, *on_completion);
}


/* Helper to initialize GNU readline properly. */

static void
setup_readline(void)
{
#ifdef SAVE_LOCALE
    char *saved_locale = strdup(setlocale(LC_CTYPE, NULL));
    if (!saved_locale)
        Py_FatalError("not enough memory to save locale");
#endif

#ifdef __APPLE__
    /* the libedit readline emulation resets key bindings etc
     * when calling rl_initialize.  So call it upfront
     */
    if (using_libedit_emulation)
        rl_initialize();

    /* Detect if libedit's readline emulation uses 0-based
     * indexing or 1-based indexing.
     */
    add_history("1");
    if (history_get(1) == NULL) {
        libedit_history_start = 0;
    } else {
        libedit_history_start = 1;
    }
    clear_history();
#endif /* __APPLE__ */

    using_history();

    rl_readline_name = "oils";
#if defined(PYOS_OS2) && defined(PYCC_GCC)
    /* Allow $if term= in .inputrc to work */
    rl_terminal_name = getenv("TERM");
#endif
    /* Force rebind of TAB to insert-tab */
    rl_bind_key('\t', rl_insert);
    /* Bind both ESC-TAB and ESC-ESC to the completion function */
    rl_bind_key_in_map ('\t', rl_complete, emacs_meta_keymap);
    rl_bind_key_in_map ('\033', rl_complete, emacs_meta_keymap);
#ifdef HAVE_RL_RESIZE_TERMINAL
    /* Set up signal handler for window resize */
    sigwinch_ohandler = PyOS_setsig(SIGWINCH, readline_sigwinch_handler);
#endif
    /* Set our hook functions */
    rl_startup_hook = on_startup_hook;
#ifdef HAVE_RL_PRE_INPUT_HOOK
    rl_pre_input_hook = on_pre_input_hook;
#endif
    /* Set our completion function */
    rl_attempted_completion_function = flex_complete;
    /* Set Python word break characters */
    completer_word_break_characters =
        rl_completer_word_break_characters =
        strdup(" \t\n`~!@#$%^&*()-=+[{]}\\|;:'\",<>/?");
        /* All nonalphanums except '.' */

    begidx = PyInt_FromLong(0L);
    endidx = PyInt_FromLong(0L);

#ifdef __APPLE__
    if (!using_libedit_emulation)
#endif
    {
        if (!isatty(STDOUT_FILENO)) {
            /* Issue #19884: stdout is not a terminal. Disable meta modifier
               keys to not write the ANSI sequence "\033[1034h" into stdout. On
               terminals supporting 8 bit characters like TERM=xterm-256color
               (which is now the default Fedora since Fedora 18), the meta key is
               used to enable support of 8 bit characters (ANSI sequence
               "\033[1034h").

               With libedit, this call makes readline() crash. */
            rl_variable_bind ("enable-meta-key", "off");
        }
    }

    /* Initialize (allows .inputrc to override)
     *
     * XXX: A bug in the readline-2.2 library causes a memory leak
     * inside this function.  Nothing we can do about it.
     */
#ifdef __APPLE__
    if (using_libedit_emulation)
        rl_read_init_file(NULL);
    else
#endif /* __APPLE__ */
        rl_initialize();

    RESTORE_LOCALE(saved_locale)
}

/* Wrapper around GNU readline that handles signals differently. */


#if defined(HAVE_RL_CALLBACK) && defined(HAVE_SELECT)

static  char *completed_input_string;
static void
rlhandler(char *text)
{
    completed_input_string = text;
    rl_callback_handler_remove();
}

static char *
readline_until_enter_or_signal(char *prompt, int *signal)
{
    char * not_done_reading = "";
    fd_set selectset;

    *signal = 0;
#ifdef HAVE_RL_CATCH_SIGNAL
    rl_catch_signals = 0;
#endif
    /* OVM_MAIN: Oil is handling SIGWINCH, so readline shouldn't handle it.
     * Without this line, strace reveals that GNU readline is constantly
     * turning it on and off.
     * */
    rl_catch_sigwinch = 0;

    rl_callback_handler_install (prompt, rlhandler);
    FD_ZERO(&selectset);

    completed_input_string = not_done_reading;

    while (completed_input_string == not_done_reading) {
        int has_input = 0;

        while (!has_input)
        {               struct timeval timeout = {0, 100000}; /* 0.1 seconds */

            /* [Bug #1552726] Only limit the pause if an input hook has been
               defined.  */
            struct timeval *timeoutp = NULL;
            if (PyOS_InputHook)
                timeoutp = &timeout;
#ifdef HAVE_RL_RESIZE_TERMINAL
            /* Update readline's view of the window size after SIGWINCH */
            if (sigwinch_received) {
                sigwinch_received = 0;
                rl_resize_terminal();
            }
#endif
            FD_SET(fileno(rl_instream), &selectset);
            /* select resets selectset if no input was available */
            has_input = select(fileno(rl_instream) + 1, &selectset,
                               NULL, NULL, timeoutp);
            if(PyOS_InputHook) PyOS_InputHook();
        }

        if(has_input > 0) {
            rl_callback_read_char();
        }
        else if (errno == EINTR) {
            int s;
#ifdef WITH_THREAD
            PyEval_RestoreThread(_PyOS_ReadlineTState);
#endif
            s = PyErr_CheckSignals();
#ifdef WITH_THREAD
            PyEval_SaveThread();
#endif
            if (s < 0) {
                rl_free_line_state();
#if defined(RL_READLINE_VERSION) && RL_READLINE_VERSION >= 0x0700
                rl_callback_sigcleanup();
#endif
                rl_cleanup_after_signal();
                rl_callback_handler_remove();
                *signal = 1;
                completed_input_string = NULL;
            }
        }
    }

    return completed_input_string;
}


#else

/* Interrupt handler */

static jmp_buf jbuf;

/* ARGSUSED */
static void
onintr(int sig)
{
    longjmp(jbuf, 1);
}


static char *
readline_until_enter_or_signal(char *prompt, int *signal)
{
    PyOS_sighandler_t old_inthandler;
    char *p;

    *signal = 0;

    old_inthandler = PyOS_setsig(SIGINT, onintr);
    if (setjmp(jbuf)) {
#ifdef HAVE_SIGRELSE
        /* This seems necessary on SunOS 4.1 (Rasmus Hahn) */
        sigrelse(SIGINT);
#endif
        PyOS_setsig(SIGINT, old_inthandler);
        *signal = 1;
        return NULL;
    }
    rl_event_hook = PyOS_InputHook;
    p = readline(prompt);
    PyOS_setsig(SIGINT, old_inthandler);

    return p;
}
#endif /*defined(HAVE_RL_CALLBACK) && defined(HAVE_SELECT) */


static char *
call_readline(FILE *sys_stdin, FILE *sys_stdout, char *prompt)
{
    size_t n;
    char *p, *q;
    int signal;

#ifdef SAVE_LOCALE
    char *saved_locale = strdup(setlocale(LC_CTYPE, NULL));
    if (!saved_locale)
        Py_FatalError("not enough memory to save locale");
    setlocale(LC_CTYPE, "");
#endif

    if (sys_stdin != rl_instream || sys_stdout != rl_outstream) {
        rl_instream = sys_stdin;
        rl_outstream = sys_stdout;
#ifdef HAVE_RL_COMPLETION_APPEND_CHARACTER
        rl_prep_terminal (1);
#endif
    }

    p = readline_until_enter_or_signal(prompt, &signal);

    /* we got an interrupt signal */
    if (signal) {
        RESTORE_LOCALE(saved_locale)
        return NULL;
    }

    /* We got an EOF, return an empty string. */
    if (p == NULL) {
        p = PyMem_Malloc(1);
        if (p != NULL)
            *p = '\0';
        RESTORE_LOCALE(saved_locale)
        return p;
    }

    /* we have a valid line */
    n = strlen(p);
    /* Copy the malloc'ed buffer into a PyMem_Malloc'ed one and
       release the original. */
    q = p;
    p = PyMem_Malloc(n+2);
    if (p != NULL) {
        strncpy(p, q, n);
        p[n] = '\n';
        p[n+1] = '\0';
    }
    free(q);
    RESTORE_LOCALE(saved_locale)
    return p;
}


/* Initialize the module */

PyDoc_STRVAR(doc_module,
"Importing this module enables command line editing using GNU readline.");

#ifdef __APPLE__
PyDoc_STRVAR(doc_module_le,
"Importing this module enables command line editing using libedit readline.");
#endif /* __APPLE__ */

PyMODINIT_FUNC
initline_input(void)
{
    PyObject *m;

#ifdef __APPLE__
    if (strncmp(rl_library_version, libedit_version_tag, strlen(libedit_version_tag)) == 0) {
        using_libedit_emulation = 1;
    }

    if (using_libedit_emulation)
        m = Py_InitModule4("line_input", readline_methods, doc_module_le,
                   (PyObject *)NULL, PYTHON_API_VERSION);
    else

#endif /* __APPLE__ */

    m = Py_InitModule4("line_input", readline_methods, doc_module,
                       (PyObject *)NULL, PYTHON_API_VERSION);
    if (m == NULL)
        return;

    PyOS_ReadlineFunctionPointer = call_readline;
    setup_readline();

    PyModule_AddIntConstant(m, "_READLINE_VERSION", RL_READLINE_VERSION);
    PyModule_AddIntConstant(m, "_READLINE_RUNTIME_VERSION", rl_readline_version);
}
