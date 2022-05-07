#### Shell Append += with Oil Values (issue #840)

var g = 2
echo g=$g

# What should happen here?

g+=1
echo g=$g

g+=1
echo g=$g

## STDOUT:
## END


#### Shell ${x:-default} with Oil values (issue #954)

var mylist = [1, 2, 3]

echo mylist ${mylist:-default}

var myint = 42

echo myint ${myint:-default}

## STDOUT:
## END


#### Shell ${a[0]} with Oil values (issue #1092)

var a = [1, 2, 3]
echo first ${a[0]}

## STDOUT:
## END


