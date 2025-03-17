
def create_context(x)
  y = 20
  binding
end

binding = create_context(10)
puts binding
puts binding.class

vars = binding.eval("local_variables")
puts vars
puts vars.class

# Why doesn't this work?
#myproc = proc { puts "x: #{x}, y: #{y}" }

# You need this longer thing
myproc = proc { puts "x: #{binding.eval("x")}, y: #{binding.eval("y")}" }

# Execute the block in the context
binding.instance_exec(&myproc)


#
# 2025-03 - var vs. setvar
#

puts ""

def outer_function
  counter = 10  # Outer function defines its own `counter`
  puts "Counter in outer_function is: #{counter}"

  # Inner function also defines its own `counter`
  inner_function = lambda do
    counter = 5  # Inner function defines its own `counter`
    puts "Mutating counter in inner_function: #{counter}"
  end

  # Calling the inner function
  inner_function.call

  # Back to outer function, `counter` remains unchanged
  puts "Counter in outer_function after inner call: #{counter}"
end

outer_function

