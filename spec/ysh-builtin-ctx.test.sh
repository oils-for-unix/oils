## our_shell: ysh
## oils_failures_allowed: 0

#### ctx push and set
var mydict = {}
ctx push (mydict) {
  ctx set (key1="value1")
  ctx set (key2="value2")
}
json write (mydict)
## STDOUT:
{
  "key1": "value1",
  "key2": "value2"
}
## END

#### ctx emit
var p = {}
ctx push (p) {
  ctx emit flag ({short_name: '-v'})
  # p => {'flag': [{short_name: '-v'}]}
  json write (p)

  ctx emit flag ({short_name: '-c'})
  # p => {'flag': [{short_name: '-v'}, {short_name: '-c'}]}
  json write (p)
}
json write (p)
## STDOUT:
{
  "flag": [
    {
      "short_name": "-v"
    }
  ]
}
{
  "flag": [
    {
      "short_name": "-v"
    },
    {
      "short_name": "-c"
    }
  ]
}
{
  "flag": [
    {
      "short_name": "-v"
    },
    {
      "short_name": "-c"
    }
  ]
}
## END
