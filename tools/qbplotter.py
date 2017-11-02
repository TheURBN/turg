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


def voxel_id(x, y, z):
    return f'{x}_{y}_{z}'


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
        print(f"Found {num_matrices} matrices")

        colors_palette = []
        object_dict = {}

        for _ in range(num_matrices):
            name_length = struct.unpack("B", qbfile.read(1))[0]
            name = struct.unpack(str(name_length) + "s", qbfile.read(name_length))[0]
            size = struct.unpack("III", qbfile.read(12))
            print(f"Loading Matrix {name} with size {size}")

            _ = struct.unpack("iii", qbfile.read(12))
            for z in range(size[2]):
                for y in range(size[1]):
                    for x in range(size[0]):
                        color = struct.unpack("I", qbfile.read(4))[0]
                        if color:
                            dec_rgb = [(color >> (8 * i)) & 255 for i in range(3)]
                            hex_color = "#{}".format(binascii.hexlify(struct.pack('BBB', *dec_rgb)).decode(encoding='UTF-8'))
                            if hex_color not in colors_palette:
                                colors_palette.append(hex_color)
                            if z_axis_orientation:
                                object_dict[voxel_id(x, z, y)] = [x, z, y, hex_color]
                            else:
                                object_dict[voxel_id(x, y, z)] = [x, y, z, hex_color]
        return object_dict, colors_palette


def optimise(object_dict):
    print("Optimising voxels...")

    def neighbour(voxel, x_diff, y_diff, z_diff):
        return voxel_id(voxel[0] + x_diff,
                        voxel[1] + y_diff,
                        voxel[2] + z_diff)

    neighbours = (
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (-1, 0, 0),
        (0, -1, 0),
        (0, 0, -1),
    )

    def is_surrounded(voxel):
        if all(map(lambda n: neighbour(voxel, *n) in object_dict, neighbours)):
            return True

        return False

    optimised = {}

    for v_id, voxel in object_dict.items():
        if not is_surrounded(voxel):
            optimised[v_id] = voxel

    gone = len(object_dict) - len(optimised)
    try:
        gone_relative = 100 - len(optimised) / len(object_dict) * 100
    except ZeroDivisionError:
        gone_relative = 0

    print("Optimised away {0} voxels ({1:.2f}%)".format(gone, gone_relative))

    return optimised


def urb_ws_plotter(object_dict, palette, pos, turg_db):
    print(f"Object contains {len(object_dict)} voxels")
    print(f"Connecting with {turg_db}")
    print(f"Plot start position {pos}")
    [print(color(chr(9608), chr_color), end='') for chr_color in palette]
    print()
    print("palette = [{}]".format(','.join(map(lambda c: f'\'{c}\'', palette))))
    print()

    db = MongoClient(turg_db).get_database()

    def docs():
        for _, o in optimise(object_dict).items():
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
    objects, palette = qb_decode(os.path.expanduser(args.src))
    pos = (args.x, args.y, args.z)
    urb_ws_plotter(objects, palette, pos, args.turg_db)
