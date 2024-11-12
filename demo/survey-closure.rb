
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

