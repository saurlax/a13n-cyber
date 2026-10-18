"""Install the pinned, checksum-verified Ghidra release during image construction."""

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "ghidra.zip"
        with urllib.request.urlopen(manifest["url"], timeout=120) as response:
            with archive.open("wb") as output:
                shutil.copyfileobj(response, output)
        with archive.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != manifest["sha256"]:
                raise RuntimeError("Ghidra archive checksum mismatch")
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(directory)
        # ZipFile does not restore Unix executable permissions.
        extracted = Path(directory) / manifest["directory"]
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                mode = entry.external_attr >> 16
                if mode & 0o111:
                    (Path(directory) / entry.filename).chmod(mode & 0o777)
        shutil.move(str(extracted), str(args.destination))


if __name__ == "__main__":
    main()
