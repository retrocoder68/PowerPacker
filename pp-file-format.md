# PowerPacker 2.0 format

## - Overview
PowerPacker is an implementation of LZSS, with some additions.
LZSS is a variant of the LZ77 compression algorithm.

One difference between LZSS and LZ77 is that LZSS uses one
bit to signal if the next chunk of data should be copied
verbatim from the compressed input or if it is a Offset-Length
pair to copy data already in the output.
In addition to this PowerPacker also uses variable bit-length
of the Offset-Length pair. There are two methods for constructing
the Offset-Length pair. One bit is used to signal which of the two methods
to use.

The compressed data is stored from the back of the file,
and also the bits in each byte is stored backwards.
This means every bit from the compressed data has to be read
separately and combined together to the desired bit length.

## - Detailed data fields
Positive indexes are counted from the start of the file, i.e. 
index 0 point to the first byte of the file.
Negative indexes are counted from the back of the file, i.e index -1 point
to the last byte of the file.

```
Index - Data type - Name - Comment
0-3     char        TAG     # This tag (PP20) marks the content of this file
                            # as compressed with PowerPacker version 2.0
4-7     char        OFFS    # Table with 4 bytes, each defining the
                            # bit length of an offset.
8-x     char        COMP    # All the compressed data, stored backwards.
                            # The beginning of the data is at the end of
                            # the file. Also the bits in each byte is stored
                            # backwards. See details below on how to read and
                            # interpret the data.
-4 - -2 char LEN            # The length of the uncompressed data is stored as
                            # a big-endian 3 byte integer at the end.
-1      char SKIP           # The last byte of the file tells how many
                            # bits that should be skipped before the real data
                            # begins when reading from COMP. Also note since
                            # the bits and data are read from the back,
                            # the bits to skip are the last bits of the
                            # COMP field.
```

## - Unpacking
The compressed data is stored as a bitstream in the COMP part of the file,
except the last bits. How many bits to exlude is given in the SKIP field.
To read out bits from the COMP field, the bit length is given and the bits are 
read one by one and a result with the wanted bit length is constructed.

Note: LSB = least significant bit

* Read bits pseudo code
```
read_bits(wanted_bit_length)
  result = 0
  result_ bit_length = 0
  byte = 0
  while result_bit_length < wanted_bit_length do
    if bits_left is 0 then
      byte = read_next_byte()
      bits_left = 8
    end if

    result = result * 2 # I.e. result is shifted left one step
    result = result + LSB(byte)
    bits_left = bits_left - 1
    result_bit_length = result_bit_length + 1
  end while

  return result
```

Note: the byte read and the bits_left data must be saved between
consecutive calls to read_bits so that the reading of bits continue
at the correct place in the bitstream

### - Interpreting the bits
The first bit of every chunk of data signals if the chunk should be copied
verbatim to the output or if it is a Offset-Length pair.

#### - Section 1: First bit is 0
This section of the unpacking algorithm is done only if the first bit is
0, otherwise it is skipped and algorithm continues with section 2.
Here data is copied verbatim from the compressed data. Data is copied one byte at a time,
and the length is given in bytes.
The length of the data to copy is given in one or more 2 bit numbers, where the 
value 3 also means to continue reading the next 2 bit number and add it to the length. 
If the this 2 bit number is also 3, add it to the length and continue reading and adding until a value less the 3 is read.

Note: Since the data is read from the end, the output buffer must also
be written from the end.

* Psuedo code
```
  copy_len = 0
loop:
  len_to_add = read_bits(2)
  copy_len = copy_len + len_to_add
  if len_to_add is 3 go back to loop

  repeat copy_len times
    byte = read_bits(8)
    write byte to output buffer
  end_repeat
```

#### Section 2: Copy Offset-Length from output buffer
In this section an Offset-Length pair is constructed and data
already output are written to the output once again.

This part start by reading a two bit number which tells how many bytes to copy.
However the value 3 has special meaning, more on that later.
The number read is also used as an index into the OFFS part of the file.
From the OFFS table the bit length of the actual offset is taken.
Then the offset is read.
Next the bytes are copied as described below.

Now onto the special case where a 3 was read.
In this case another bit is read, that signal how the offset length should
be constructed. If this bit is a 0 then the offset length is 7 bits.
if the bit is a 1 the offset length is taken from the OFFS table.
Next the offset is read.

Next the length of data to copy is calculated. A 3 bit value is read
and added to the previously read length. If the 3 bit value was a 7 then the process
continues, reading another 3 bit value and adding to the length.
This process continues until a value less then 7 is read.

* Pseudo code
```
  copy_len = read_bits(2)
  offset_len = OFFS[copy_len]
  if copy_len is not 3 then
    offset = read_bits(offset_len)

  else if copy_len is 3 then # Special case
    flag = read_bits(1)
    if flag is 0 then
      offset = read_bits(7)
    else if flag is 1 then
      offset = read_bits(offset_len)
    end_if

   loop:
    len_to_add = read_bits(3)
    copy_len = copy_len + len_to_add
    if len_to_add is 7 go back to loop
  end_if
```

### - Copying the data
The length of the data to copy is adjusted by 2. I.e reading a length of 0 means
2 bytes should be copied.
The bytes are copied to the output, given the offset and the length in bytes.
Remember that the reading and writing is done from the back and also note that
this is a sliding window, so the actual offset is always
relative to the current write position. 

* Psuedo code
```
  copy_len = copy_len + 2
  repeat copy_len times
    byte = output[current_write_index + 1 + offset]
    output[current_write_index] = byte
    current_write_index = current_write_index - 1
  end_repeat
```

## - Packing
TBC
