import argparse
import json
import os

from utils.yaffs import mix_spare

parser = argparse.ArgumentParser(description="Keitai YAFFS2 Detect")
parser.add_argument("input")
parser.add_argument("config")
parser.add_argument(
    "-t",
    "--threshold",
    help="Threshold of the sequence id that is considered in the same file system as another one.",
    default=5000,
    type=int,
)
parser.add_argument(
    "-s",
    "--mix-spare",
    help="Mix spare using filepath '[input (without extension)].oob'.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

with open(args.config, "r", encoding="utf-8") as file:
    config = json.load(file)

with open(args.input, "rb") as file:
    data = file.read()

if args.mix_spare:
    oob = os.path.join(
        os.path.dirname(args.input),
        f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
    )
    with open(oob, "rb") as file:
        spare = file.read()
    data = mix_spare(data, spare, config)

seq_ids = {}
for i in range(0, len(data), config["data_size"] + config["spare_size"]):
    metadata = {}
    for key, off in config["spare_layout"].items():
        metadata[key] = int.from_bytes(
            data[i + config["data_size"] + off : i + config["data_size"] + off + 4],
            "little",
        )

    if metadata["empty"] != 0xFFFFFFFF or metadata["seq_id"] == 0xFFFFFFFF:
        continue
    seq_ids[i] = metadata["seq_id"]

start_points = []

while len(seq_ids) > 0:
    ref = max(seq_ids.values())
    current_start = max(seq_ids) + config["data_size"] + config["spare_size"]
    current_end = 0
    for k, v in seq_ids.items():
        if v >= ref - args.threshold:
            current_start = min(current_start, k)
            current_end = max(
                current_end, k + config["data_size"] + config["spare_size"]
            )
    for k in list(seq_ids):
        if current_start <= k < current_end:
            del seq_ids[k]
    start_points.append(current_start)

start_points.sort()

final = []
for i in range(len(start_points)):
    if i == len(start_points) - 1:
        end = len(data)
    else:
        end = start_points[i + 1]
    final.append({"start": start_points[i], "end": end})
print('"partitions":', json.dumps(final))
