import argparse
import binascii
import datetime
import os
import struct
import sys

from colors import color
from pymongo import MongoClient

# Qubicle Binary is an exchange format that stores voxel data in binary form.
# http://www.minddesk.com/wiki/index.php?title=Qubicle_Constructor_1:Data_Exchange_With_Qubicle_Binary

parser = argparse.ArgumentParser()
parser.add_argument("--src", help=".qb file location", type=str)
parser.add_argument("--x", help="X coordinate", default=0, type=int)
parser.add_argument("--y", help="Y coordinate", default=0, type=int)
parser.add_argument("--z", help="Z coordinate", default=0, type=int)
parser.add_argument("--turg-db", help="theurbn db", default='', type=str)
args = parser.parse_args()

SPOT_FLAG_COLOR = '#ff00ff'


def qb_decode(qb_file_path):
    print(f"Loading {qb_file_path}")
    with open(qb_file_path, 'rb') as qbfile:
        version = struct.unpack("I", qbfile.read(4))[0]
        if version != 0x0101:  # 1.1.0.0
            print("Unsupported QB format detected")
            sys.exit(1)
        color_format = 'RGBA' if struct.unpack("I", qbfile.read(4))[0] is 0 else 'BGRA'
        if color_format is not 'RGBA':
            print("Unsupported colour {color_format} format detected")
            sys.exit(1)
        z_axis_orientation = struct.unpack("I", qbfile.read(4))[0]
        is_compressed = struct.unpack("I", qbfile.read(4))[0]
        if is_compressed:
            print("Unsupported RLE compression detected")
            sys.exit(1)
        _ = struct.unpack("I", qbfile.read(4))[0]  # Visibility-Mask encoded
        num_matrices = struct.unpack("I", qbfile.read(4))[0]
        for _ in range(num_matrices):
            name_length = struct.unpack("B", qbfile.read(1))[0]
            name = struct.unpack(str(name_length) + "s", qbfile.read(name_length))[0]
            size = struct.unpack("III", qbfile.read(12))
            print(f"Loading Matrix {name} with size {size}")

            _ = struct.unpack("iii", qbfile.read(12))
            object_list = list()
            colors_pallete = list()
            for z in range(size[2]):
                for y in range(size[1]):
                    for x in range(size[0]):
                        color = struct.unpack("I", qbfile.read(4))[0]
                        if color:
                            dec_rgb = [(color >> (8 * i)) & 255 for i in range(3)]
                            hex_color = "#{}".format(binascii.hexlify(struct.pack('BBB', *dec_rgb)).decode(encoding='UTF-8'))
                            if hex_color not in colors_pallete:
                                colors_pallete.append(hex_color)
                            if z_axis_orientation:
                                object_list.append((x, z, y, hex_color))
                            else:
                                object_list.append((x, y, z, hex_color))
            return object_list, colors_pallete


def urb_ws_plotter(object_list, pallete, pos, turg_db):
    print(f"Object contains {len(object_list)} voxels")
    print(f"Connecting with {turg_db}")
    print(f"Plot start position {pos}")
    [print(color(chr(9608), chr_color), end='') for chr_color in pallete]
    print()

    db = MongoClient(turg_db).get_database()

    def docs():
        for o in object_list:
            if o[3] == SPOT_FLAG_COLOR:
                print(f"Spot flag at {o[0]}x{o[1]}x{o[2]}")
                name = f"Spot{o[0]}{o[1]}"
            else:
                name = None
            yield {'x': o[0] + pos[0],
                   'y': o[1] + pos[1],
                   'z': o[2] + pos[2],
                   'owner': o[3],
                   'name': name,
                   'updated': datetime.datetime.now()}

    result = db.data.insert_many(docs(), ordered=False)
    print(f"Inserted {len(result.inserted_ids)} voxels")

if __name__ == '__main__':
    pic = qb_decode(os.path.expanduser(args.src))
    pos = (args.x, args.y, args.z)
    urb_ws_plotter(pic[0], pic[1], pos, args.turg_db)
