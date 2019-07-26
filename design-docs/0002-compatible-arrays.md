Bash/ksh Compatible Arrays
--------------------------

Work done in July 2019.

- [0002-compatible-arrays.md][] - Parsing Bash is Undecidable
  - syntax and semantics
    - assignments a['x']=1
    - literals a=(['x']=1)  
  - behavior within (( )) -- coercion to integer
  - TODO: should go in known-differences?
  - see doc/osh-data-model too.  Does that help end users?



