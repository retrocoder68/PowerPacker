#!/usr/bin/env python
# Copyright (C) 2020 skywalker a.k.a. J.Karlsson <j.karlsson@retrocoder.se>

import argparse
import struct

class PowerPacker:
    def __init__(self):
        self.src = b""
        self.src_i = 0
        self.dst = b""
        self.dst_i = 0

        self.bits = 0
        self.bits_left = 0

    def unpack_file(self, file_name):
        with open(file_name, "rb") as f:
            return self.unpack(f.read())

    def unpack(self, data):
        self.src = data
        self.src_i = len(self.src) - 4

        self.bits = 0
        self.bits_left = 0

        if self.src[:4] != b"PP20":
            return b"Not a PowerPacked file"

        info = struct.unpack(">I", self.src[self.src_i:])[0]
        self.src_i -= 1
        sz = info >> 8
        self.dst = bytearray(sz)
        self.dst_i = sz-1
        skip_bits = info & 0xFF
        self.read_bits(skip_bits)

        offs_len = [0]*4
        offs_len[0] = self.src[4]
        offs_len[1] = self.src[5]
        offs_len[2] = self.src[6]
        offs_len[3] = self.src[7]

        while(True):
            copy_bytes = self.read_bits(1)
            if(copy_bytes == 0):
                copy_bytes = 1
                while(True):
                    copy_len = self.read_bits(2)
                    copy_bytes += copy_len
                    if (copy_len != 3): break
                for _ in range(copy_bytes):
                    self.dst[self.dst_i] = self.read_bits(8)
                    self.dst_i -= 1
                    if (self.dst_i < 0): return self.dst

            copy_bytes = self.read_bits(2)
            offset_len = offs_len[copy_bytes]
            if copy_bytes != 3:
                offset = self.read_bits(offset_len)
            else:
                if self.read_bits(1) == 0:
                    offset = self.read_bits(7)
                else:
                    offset = self.read_bits(offset_len)

                while(True):
                    copy_len = self.read_bits(3)
                    copy_bytes += copy_len
                    if copy_len != 7: break

            copy_bytes += 2
            for _ in range(copy_bytes):
                self.dst[self.dst_i] = self.dst[self.dst_i + 1 + offset]
                self.dst_i -= 1
            if self.dst_i < 0: return self.dst

    def read_bits(self, bit_count):
        result = 0

        for _ in range(bit_count):
            if(self.bits_left == 0):
                self.bits = self.src[self.src_i]
                self.src_i -= 1
                self.bits_left = 8

            result = result << 1
            result |= self.bits & 1
            self.bits = self.bits >> 1
            self.bits_left -= 1

        return result

def main():
    parser = argparse.ArgumentParser("PowerPacker 2.0")
    parser.add_argument('filename', help='the file to unpack')
    args = parser.parse_args()
    args.filename
    pp = PowerPacker()
    unpacked_data = pp.unpack_file(args.filename)
    print(unpacked_data)

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
