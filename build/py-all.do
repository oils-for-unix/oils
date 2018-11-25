for d in *.pyflags; do
  echo "${d%.pyflags}.pybuild"
done | xargs redo-ifchange
