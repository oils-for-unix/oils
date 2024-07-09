---
default_highlighter: oils-sh
---

BYO - Protocols for Build, Test, Deploy
===========

Points of reference:

- 12 factor app for Hosting (Heroku)
- CGI / FastCGI
- TAP - Test Anything Protocol

Derived from usage in Oils itself.

Name:

- stood for Bash YSH OSH
- But "bring your own" is a good acronym

## Detection

    BYO_COMMAND=detect ./any-executable </dev/null
    list-tests
    run-tests

    # must exit 66?  66 is ASCII 'B'
    # and print env


## Testing

    BYO_COMMAND=list-tests   

    BYO_COMMAND=run-tests   
    BYO_ARG=foo

## Benchmarking

TSV?

## Build

Ninja


## Deploy

Hm

## Logs

- Usage logs
- Monitoring / latency logs
