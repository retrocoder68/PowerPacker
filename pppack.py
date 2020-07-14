#!/usr/bin/env python
# Copyright (C) 2020 skywalker a.k.a. J.Karlsson <j.karlsson@retrocoder.se>

import argparse
import math
import struct

class PowerPacker:
    def __init__(self):
        self.src = b""
        self.src_i = 0
        self.dst = bytearray(1)
        self.dst_i = 0

        self.bits = 0
        self.bits_left = 0

        self.look_ahead = bytearray()
        self.window = bytearray()

    def pack_file(self, file_name):
        with open(file_name, "rb") as f:
            return self.pack(f.read())

    def pack(self, data):
        self.src = data
        self.src_i = len(self.src)-1

        self.dst = bytearray(1)
        self.dst_i = 0

        self.bits = 0
        self.bits_left = 0

        self.look_ahead = bytearray()
        self.window = bytearray()

        # Setup the offset length table based on window size
        window_len = 13
        self.offs_len = [0]*4
        self.offs_len[0] = window_len - 4
        self.offs_len[1] = window_len - 3
        self.offs_len[2] = window_len - 1
        self.offs_len[3] = window_len

        # TAG
        self.dst[0:4] = b"PP20"

        # OFFS
        self.dst[5:8] = self.offs_len
        self.dst_i = 7

        # COMP
        compress_instr = []
        while self.fill_look_ahead():
            offset, length = self.find_match()
            if offset != -1:
                compress_instr.append((offset, length))
                match = self.look_ahead[:length]
                self.look_ahead = self.look_ahead[length:]
                self.window += match
            else:
                c = self.look_ahead[0]
                self.look_ahead = self.look_ahead[1:]
                compress_instr.append((-1,c))
                self.window.append(c)

            if len(self.window) > 4096:
                excess = len(self.window) - 4096
                self.window = self.window[excess:]

        compress_instr.reverse()
        tmp = []
        for i,_ in enumerate(compress_instr):
            if compress_instr[i][0] == -1 and \
                (i == len(compress_instr) - 1 or compress_instr[i+1][0] != -1):
                tmp.append((0, compress_instr[i][1]))
            else:
                tmp.append(compress_instr[i])
        compress_instr = tmp

        verbatim = bytearray()
        chunk_start_written = True
        for pack_instr, data in compress_instr:
            if pack_instr == -1: # Add char to verbatim string
                verbatim.append(data)
            elif pack_instr == 0: # Add last char and write verbatim string
                verbatim.append(data)
                for c in verbatim:
                    self.write_bits(8, c)
                count = len(verbatim)
                if count <= 3:
                    self.write_bits(2, count - 1)
                else:
                    count = count - 1
                    rest = count % 3
                    self.write_bits(2, rest)
                    count -= rest
                    while count > 0:
                        self.write_bits(2, 3)
                        count -= 3

                # Write start of chunk bit
                self.write_bits(1, 0)
                chunk_start_written = True

                verbatim = bytearray()

            else: # Write copy from window data
                # If the previous pack instruction was also a 'copy from window'
                # then the start of chunk bit has not been written and needs
                # to be written now.
                if not chunk_start_written:
                    self.write_bits(1, 1)

                offset = pack_instr
                length = data
                if length <= 4:
                    offset_index = data - 2
                    offset_len = self.offs_len[offset_index]
                    self.write_bits(offset_len, offset - 1)
                    self.write_bits(2, length - 2)
                else:
                    count = length - 5
                    if count < 7:
                        self.write_bits(3, count)
                    else:
                        rest = count % 7
                        self.write_bits(3, rest)
                        count -= rest
                        while count > 0:
                            self.write_bits(3, 7)
                            count -= 7

                    offset_len = max(self.offs_len[3], 7)
                    self.write_bits(offset_len, offset - 1)
                    offs_flag = offset_len != 7
                    self.write_bits(1, offs_flag)
                    self.write_bits(2, 3)



                chunk_start_written = False

        skip = self.bits_left
        self.write_bits(self.bits_left, 0)
        self.dst_i += 1

        # LEN
        self.dst[self.dst_i:self.dst_i+2] = struct.pack(">I", len(self.src))[1:]
        self.dst_i += 3

        # SKIP
        self.dst[self.dst_i:self.dst_i+1] = [skip]

        return self.dst

    def write_bits(self, bit_count, value):
        for _ in range(bit_count):
            if self.bits_left == 0:
                self.dst_i += 1
                self.dst[self.dst_i:self.dst_i] = [0]
                self.bits_left = 8

            self.dst[self.dst_i] = self.dst[self.dst_i] << 1 | value & 1
            value = value >> 1
            self.bits_left -= 1

    def fill_look_ahead(self):
        while len(self.look_ahead) < 255:
            if self.src_i < 0:
                break
            self.look_ahead.append(self.src[self.src_i])
            self.src_i -= 1

        return len(self.look_ahead) > 0

    def find_match(self):
        if len(self.look_ahead) >= 2:
            for match_length in range(len(self.look_ahead), 1, -1):
                window_size = 0
                if match_length > 4:
                    window_size = 2 ** max(self.offs_len[3], 7)
                else:
                    window_size = 2 ** self.offs_len[match_length-2]
                i = self.window.rfind(self.look_ahead[:match_length])
                if i != -1:
                    j = len(self.window) - i
                    if j-2 <= window_size:
                        return (j, match_length)

        return (-1, 0)

def main():
    parser = argparse.ArgumentParser("PowerPacker 2.0")
    parser.add_argument('filename', help='the file to pack')
    args = parser.parse_args()
    pp = PowerPacker()
    packed_data = pp.pack_file(args.filename)
    out_filename = args.filename+".pp"
    with open(out_filename, "wb") as f:
        f.write(packed_data)
    print(f"{out_filename} successfully created")

if __name__ == "__main__":
    main()

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as 
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
