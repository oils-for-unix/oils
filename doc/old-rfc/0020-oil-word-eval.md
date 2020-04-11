Oil Word Evaluation
-------------------

- oil-word-eval
  - implies static glob
  - implies no splitting
	- @ifssplit(a)
	- local foo=$(echo hi)

	for $x in @ifssplit(lines); do
		echo $x
	done

	for x in @ifssplit(lines) {
		echo $x
	}

  split(lines, :IFS)  # atom syntax is nice
                      # synonym for interned string literal?
                      # what is the type of it though?
                      # how='IFS', how='awk', how='python'

                      # how=:Delim(' ')

  or split(lines, 'IFS')

  split(lines, 'IFS')
