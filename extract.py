import argparse
import json
import os

from utils.yaffs import extract_partition, mix_spare

parser = argparse.ArgumentParser(description="Keitai YAFFS2 Extractor")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument("config")
parser.add_argument(
    "-d",
    "--show-deleted",
    help="Show deleted files in DELETED subfolder.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-m",
    "--show-missing",
    help="Show entries with missing parents in MISSING subfolder.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-u",
    "--try-undelete",
    help="Try to restore latest version of a file marked as deleted.",
    action=argparse.BooleanOptionalAction,
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

os.makedirs(args.output, exist_ok=False)

if len(config["partitions"]) == 0:
    extract_partition(
        data,
        config,
        args.output,
        args.show_deleted,
        args.show_missing,
        args.try_undelete,
    )
else:
    for i, r in enumerate(config["partitions"]):
        dst = os.path.join(args.output, str(i))
        os.makedirs(dst, exist_ok=False)
        extract_partition(
            data[r["start"] : r["end"]],
            config,
            dst,
            args.show_deleted,
            args.show_missing,
            args.try_undelete,
        )
