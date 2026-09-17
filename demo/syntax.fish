set name "world"

# string interpolation
echo "hello $name"

# if uses end, not fi
if test -f /etc/os-release
    echo "linux"
end

# for loop
for i in (seq 1 5)
    echo $i
end

# function definition
function greet --description "say hello"
    echo "hello $argv[1]"
end

greet

# pipe
echo "hello" | string upper
