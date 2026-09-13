"""Verify the generated lettersanity room with stock server check handling."""
import asyncio
import copy
import io
import json
import logging
from pathlib import Path
import sys
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worlds
from MultiServer import Context, register_location_checks
from worlds.AutoWorld import data_package_checksum
from worlds.ctr import ctrAPWorld
from worlds.ctr.custom_lettersanity import restore_custom_letter_wire


async def main():
    room = Path(sys.argv[1])
    with zipfile.ZipFile(room) as archive:
        member = next(n for n in archive.namelist() if n.endswith(".archipelago"))
        data = Context.decompress(archive.read(member))
    game = ctrAPWorld.game
    package = data["datapackage"][game]
    canonical = worlds.network_data_package["games"][game]
    assert package["item_name_to_id"] == canonical["item_name_to_id"]
    assert set(package["location_name_to_id"].values()) == set(canonical["location_name_to_id"].values())
    assert data_package_checksum(dict(sorted((k, v) for k, v in package.items() if k != "checksum"))) == package["checksum"]
    wire = data["slot_data"][1]
    letters = wire["custom_lettersanity_checks"]
    selection = restore_custom_letter_wire(letters, (1,))
    assert len(selection[1]) == 2
    checks = [code for code in letters["tracks"][0]["locations"] if code >= 0]
    checks.append(wire["custom_tracks"]["tracks"][0]["locations"]["ctr"])
    assert checks[-1] == 35023000
    checks += [code for codes in wire["lettersanity_checks"]["locations"].values()
               for code in codes if 35012548 <= code <= 35012553]
    assert len(checks) == 7
    labels = {code: name for name, code in package["location_name_to_id"].items()}
    for code in checks:
        assert code in data["locations"][1]
        if code >= 35020000:
            assert labels[code].startswith("Baby T Park: ")
    logger = logging.getLogger("letter-room-proof")
    logger.setLevel(logging.INFO)
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)
    pristine = copy.deepcopy(worlds.network_data_package)
    with patch.object(worlds, "network_data_package", copy.deepcopy(pristine)):
        ctx = Context("127.0.0.1", 0, "", "", 1, 10, False, logger=logger)
        ctx._load(copy.deepcopy(data), {}, False)
        messages = []
        ctx.broadcast_team = lambda team, msgs: messages.extend(copy.deepcopy(msgs))
        ctx.broadcast = lambda endpoints, msgs: None
        for code in checks:
            register_location_checks(ctx, 0, 1, [code])
            assert code in ctx.location_checks[0, 1]
            before = len(messages)
            register_location_checks(ctx, 0, 1, [code])
            assert len(messages) == before
            assert labels[code] in output.getvalue()
        save = ctx.get_save()
        with patch.object(worlds, "network_data_package", copy.deepcopy(pristine)):
            restored = Context("127.0.0.1", 0, "", "", 1, 10, False, logger=logger)
            restored._load(copy.deepcopy(data), {}, False)
            restored.set_save(save)
        assert restored.location_checks[0, 1] == ctx.location_checks[0, 1]
        assert restored.location_names[game] == ctx.location_names[game]
    logger.removeHandler(handler)
    room.with_suffix(".slot-data.json").write_text(json.dumps(wire, indent=2))
    room.with_suffix(".proof.json").write_text(json.dumps({
        "checks": {str(c): labels[c] for c in checks},
        "checksum": package["checksum"], "server_log": output.getvalue()}, indent=2))
    print("PASS: seven actual-room custom/trial letter and CTR checks, stock-server labels, repeat dedupe and save restore")


if __name__ == "__main__":
    asyncio.run(main())
