import argparse
import re

parser = argparse.ArgumentParser(description="Keitai NAND List Apps")
parser.add_argument("input")

args = parser.parse_args()

with open(args.input, "rb") as file:
    data = file.read()

print(
    "\n".join(
        sorted(
            set(
                b.decode("cp932", errors="ignore")
                for b in re.findall(rb"AppName\x20+=\x20+([^\r\n\x00]+)", data)
            )
        )
    )
)
