services/
=========

This directory is for integration with cloud services, e.g. code we don't
control.

Generally it's better to write plain shell scripts and call them from a config
file (e.g. YAML), rather than embedding shell in the config.  Then it can be
tested separately and ported to different platforms.
