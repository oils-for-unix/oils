#!/usr/bin/env node

function main() {
  var hexdigits = '0123456789abcdef'
  for (var i = 0; i < 16; ++i) {
    for (var j = 0; j < 16; ++j) {
      for (var k = 0; k < 16; ++k) {
        var hexbyte = hexdigits[i] + hexdigits[j] + hexdigits[k];

        var byte = hexbyte;
        // JS doesn't have replaceAll() for a fixed string
        // https://stackoverflow.com/questions/5649403/how-to-use-replaceall-in-javascript
        byte = byte.replace(/0/g, '0000')
        byte = byte.replace(/1/g, '0001')
        byte = byte.replace(/2/g, '0010')
        byte = byte.replace(/3/g, '0011')

        byte = byte.replace(/4/g, '0100')
        byte = byte.replace(/5/g, '0101')
        byte = byte.replace(/6/g, '0110')
        byte = byte.replace(/7/g, '0111')

        byte = byte.replace(/8/g, '1000')
        byte = byte.replace(/9/g, '1001')
        byte = byte.replace(/a/g, '1010')
        byte = byte.replace(/b/g, '1011')

        byte = byte.replace(/c/g, '1100')
        byte = byte.replace(/d/g, '1101')
        byte = byte.replace(/e/g, '1110')
        byte = byte.replace(/f/g, '1111')

        //print(byte)

        ones = byte.replace(/0/g, '')
        if (ones.length == 11) {
          console.log(hexbyte, byte)
        }
      }
    }
  }
}


main()
