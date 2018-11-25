for d in *.pyflags; do
  echo "${d%.pyflags}.pyclean"
done | xargs redo
