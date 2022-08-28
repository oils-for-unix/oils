prebuilt/
=========

These files are built from the repo and committed back to git.  We generally
avoid this, but doing so has benefits:

- Contributors don't need a working `mycpp` in all cases
- ASDL and mycpp fundamentally have circular dependencies, so committing
  prebuilt files breaks this loop.
