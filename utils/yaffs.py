import os

CHUNK_TYPE_FILE = 1
CHUNK_TYPE_DIR = 3
CHUNK_TYPE_PIPE = 6


def generate_entry(metadata, path):
    if metadata["generated"]:
        return
    obj_ty = metadata["obj_id"] >> 0x1C
    if metadata["undelete"]:
        metadata["name"] = "del." + metadata["name"]
    name = metadata["name"]
    full_path = os.path.join(path, name)
    if os.path.exists(full_path):
        count = 0
        while os.path.exists(full_path):
            count += 1
            name = f"dup_{count}." + metadata["name"]
            full_path = os.path.join(path, name)
    if obj_ty in [CHUNK_TYPE_FILE, CHUNK_TYPE_PIPE]:
        with open(full_path, "wb") as file:
            file.write(metadata["data"])
    elif obj_ty == CHUNK_TYPE_DIR:
        os.mkdir(full_path)
    metadata["name"] = name
    metadata["generated"] = True


def extract_partition(
    data, config, dst, show_deleted=False, show_missing=False, try_undelete=False
):
    entries_per_id = {}
    for i in range(0, len(data), config["data_size"] + config["spare_size"]):
        metadata = {}
        for key, off in config["spare_layout"].items():
            metadata[key] = int.from_bytes(
                data[i + config["data_size"] + off : i + config["data_size"] + off + 4],
                "little",
            )

        if metadata["empty"] != 0xFFFFFFFF or metadata["seq_id"] == 0xFFFFFFFF:
            continue
        metadata["obj_id"] = metadata["obj_id"]
        metadata["header"] = bool(metadata["chk_id"] & 0x80000000)
        metadata["flagu1"] = bool(metadata["chk_id"] & 0x40000000)
        metadata["flagu2"] = bool(metadata["chk_id"] & 0x20000000)

        if metadata["header"]:
            metadata["prt_id"] = metadata["chk_id"] & 0x1FFFFFFF
            metadata["chk_id"] = 0
            obj_ty = int.from_bytes(data[i + 0x0 : i + 0x4], "little")
            assert obj_ty == (metadata["obj_id"] >> 0x1C), hex(i)
            assert (
                int.from_bytes(data[i + 0x4 : i + 0x8], "little") == metadata["prt_id"]
            ), hex(i)
            metadata["data"] = bytearray()
            if obj_ty == CHUNK_TYPE_FILE or obj_ty == CHUNK_TYPE_PIPE:
                assert (
                    int.from_bytes(data[i + 0x124 : i + 0x128], "little")
                    == metadata["size"]
                ), hex(i)
                if obj_ty == CHUNK_TYPE_PIPE:
                    metadata["data"] += data[i + 0x200 : i + config["data_size"]]
                    if len(metadata["data"]) >= metadata["size"]:
                        metadata["data"] = metadata["data"][: metadata["size"]]
            elif obj_ty == CHUNK_TYPE_DIR:
                assert metadata["size"] == 0x00000000, hex(i)
                assert (
                    int.from_bytes(data[i + 0x124 : i + 0x128], "little") == 0xFFFFFFFF
                ), hex(i)
            else:
                continue

            off = i + 0xA
            metadata["name"] = b""
            while data[off] != 0:
                metadata["name"] += bytes([data[off]])
                off += 1
            metadata["name"] = metadata["name"].decode("ascii", errors="ignore")
        else:
            metadata["obj_id"] = metadata["obj_id"] | 0x10000000
            metadata["chk_id"] = metadata["chk_id"] & 0x1FFFFFFF
            metadata["data"] = data[i : i + config["data_size"]]
        metadata["offset"] = i
        lst = entries_per_id.get(metadata["obj_id"], [])
        lst.append(metadata)
        entries_per_id[metadata["obj_id"]] = lst
    full_entries = {}
    for idx, entries in entries_per_id.items():
        entries.sort(key=lambda x: (x["chk_id"], -x["seq_id"], -x["offset"]))
        metadata = dict(entries[0])
        if metadata["chk_id"] != 0 or not metadata["header"]:
            print("No header chunk for Object ID", idx, "at", hex(metadata["offset"]))
            continue
        metadata["undelete"] = False
        if metadata["prt_id"] != 1 and metadata["prt_id"] <= 4 and try_undelete:
            for e in entries:
                if e["chk_id"] > 0:
                    break
                elif (
                    (e["prt_id"] == 1 or e["prt_id"] > 4)
                    and e["chk_id"] == 0
                    and e["header"]
                ):
                    metadata = dict(e)
                    break
            metadata["undelete"] = True
        del metadata["chk_id"]
        del metadata["header"]
        if len(metadata["data"]) < metadata["size"]:
            chk_id = 1
            for e in entries:
                if e["chk_id"] > chk_id:
                    print("Missing chunk for Object ID", idx, "at", hex(metadata["offset"]))
                    break
                elif e["chk_id"] == chk_id:
                    # assert metadata["size"]==e["size"], "%d %d"%(metadata["size"], e["size"])
                    metadata["data"] += e["data"]
                    if len(metadata["data"]) >= metadata["size"]:
                        metadata["data"] = metadata["data"][: metadata["size"]]
                        break
                    chk_id += 1
        if len(metadata["data"]) < metadata["size"]:
            continue
        metadata["generated"] = False
        full_entries[idx] = metadata

    for idx, metadata in full_entries.items():
        if metadata["generated"]:
            continue
        parent = metadata["prt_id"]
        order = [metadata]
        while parent > 4:
            if (CHUNK_TYPE_DIR << 0x1C) | parent in full_entries:
                pm = full_entries[(CHUNK_TYPE_DIR << 0x1C) | parent]
                parent = pm["prt_id"]
                order.insert(0, pm)
            else:
                break

        path = dst
        if parent != 1 and parent <= 4:
            if show_deleted:
                print("Deleted", parent, metadata["name"])
                path = os.path.join(path, "DELETED", str(parent))
                os.makedirs(path, exist_ok=True)
            else:
                continue
        if parent > 4:
            if show_missing:
                print("Missing parent", parent, metadata["name"])
                path = os.path.join(path, "MISSING", str(parent))
                os.makedirs(path, exist_ok=True)
            else:
                continue
        for pm in order:
            generate_entry(pm, path)
            path = os.path.join(path, pm["name"])


def mix_spare(data, spare, config):
    assert (len(data) // config["data_size"]) == (
        len(spare) // config["spare_size"]
    ), "Data and spare size do not match."

    new_data = bytearray()
    for i in range(len(data) // config["data_size"]):
        new_data += data[i * config["data_size"] : (i + 1) * config["data_size"]]
        new_data += spare[i * config["spare_size"] : (i + 1) * config["spare_size"]]
    return bytes(new_data)
