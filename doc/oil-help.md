---
in_progress: yes
css_files: ../web/base.css ../web/manual.css ../web/help.css ../web/toc.css
body_css_class: width40 help-body
---

Oil Help
========

<div id="toc">
</div>

<h2 id="overview">Overview</h2>

### Usage

This section describes how to use the Oil binary.

<h4 id="oil-usage"><code>bin/oil</code> Usage</h4>

    Usage: oil  [OPTION]... SCRIPT [ARG]...
           oil [OPTION]... -c COMMAND [ARG]...

`bin/oil` is the same as `bin/osh` with a the `oil:all` option group set.  So
`bin/oil` also accepts shell flags.

    oil -c 'echo hi'
    oil myscript.oil
    echo 'echo hi' | oil

<h4 id="bundle-usage">App Bundle Usage</h4>

    Usage: oil.ovm MAIN_NAME [ARG]...
           MAIN_NAME [ARG]...

oil.ovm behaves like busybox.  If it's invoked through a symlink, e.g. 'osh',
then it behaves like that binary.  Otherwise the binary name can be passed as
the first argument, e.g.:

    oil.ovm osh -c 'echo hi'

