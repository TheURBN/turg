import argparse
import asyncio
import os
import struct
import sys
import random
import time
import aiohttp

# Qubicle Binary is an exchange format that stores voxel data in binary form.
# http://www.minddesk.com/wiki/index.php?title=Qubicle_Constructor_1:Data_Exchange_With_Qubicle_Binary

parser = argparse.ArgumentParser()
parser.add_argument("--src", help=".qb file location", type=str)
parser.add_argument("--x", help="X coordinate", default=0, type=int)
parser.add_argument("--y", help="Y coordinate", default=0, type=int)
parser.add_argument("--z", help="Z coordinate", default=0, type=int)
parser.add_argument("--owner", help="owner id", default=1, type=int)
parser.add_argument("--turg-url", help="theurbn backend url",
                    default="https://turg-svc.herokuapp.com/v1/ws/")
parser.add_argument("--sleep", help="plot delay in ms", default=50, type=int)
args = parser.parse_args()


def qb_to_list(qb_file_path):
    print(f"Loading {qb_file_path}")
    with open(qb_file_path, 'rb') as qbfile:
        version = struct.unpack("I", qbfile.read(4))[0]
        if version != 0x0101:  # 1.1.0.0
            print("Unsupported QB format detected")
            sys.exit(1)
        color_format = 'RGBA' if struct.unpack("I", qbfile.read(4))[0] is 0 else 'BGRA'
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
            for z in range(size[2]):
                for y in range(size[1]):
                    for x in range(size[0]):
                        color = struct.unpack("I", qbfile.read(4))[0]
                        if color:
                            if z_axis_orientation:
                                object_list.append((x, z, y))
                            else:
                                object_list.append((x, y, z))
            return object_list


async def urb_ws_plotter(object_list, start_position, owner, turg_url, delay):
    print(f"Object contains {len(object_list)} voxels")
    print(f"Plot start position {start_position}")
    print(f"Owner {owner}")
    print(f"Connecting with {turg_url}")
    session = aiohttp.ClientSession()
    async with session.ws_connect(turg_url) as ws:
        for c, voxel in enumerate(object_list):
            await ws.send_json({'type': 'update',
                                'id': random.getrandbits(128),
                                'args': {'x': start_position[0] + voxel[0],
                                         'y': start_position[1] + voxel[1],
                                         'z': start_position[2] + voxel[2],
                                         'owner': owner}})
            if c % 100 == 0:
                print(f"{c}/{len(object_list)} voxels")
            time.sleep(delay/1000)
    session.close()


if __name__ == '__main__':
    pic = qb_to_list(os.path.expanduser(args.src))
    pos = (args.x, args.y, args.z)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(urb_ws_plotter(pic, pos, args.owner,
                                           args.turg_url, args.sleep))
