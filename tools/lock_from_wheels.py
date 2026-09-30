import email
import hashlib
import re
import sys
import zipfile
from pathlib import Path

wheelhouse, output = map(Path, sys.argv[1:])
if output.exists():
    raise SystemExit(f"Refusing to overwrite {output}; review a new candidate")
wheels = sorted(wheelhouse.glob("*.whl"))
if not wheels:
    raise SystemExit("No wheels found")
if any(p.suffix != ".whl" for p in wheelhouse.iterdir()):
    raise SystemExit("Wheel directory contains unexpected entries")
records = {}
for wheel in wheels:
    with zipfile.ZipFile(wheel) as archive:
        names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise SystemExit(f"Ambiguous metadata: {wheel.name}")
        metadata = email.message_from_bytes(archive.read(names[0]))
        name = re.sub(r"[-_.]+", "-", metadata["Name"]).lower()
        version = metadata["Version"]
        if name in records:
            raise SystemExit(f"Duplicate distribution: {name}")
        with wheel.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        records[name] = f"{name}=={version} --hash=sha256:{digest}"
with output.open("x", encoding="utf-8") as stream:
    stream.write("\n".join(records[n] for n in sorted(records)) + "\n")
print(f"Wrote {len(records)} pinned wheel requirements to {output}")
