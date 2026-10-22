import zipfile
from pathlib import Path


def unpack(archive_path, target):
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.namelist():
            destination = Path(target) / member
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(member))
