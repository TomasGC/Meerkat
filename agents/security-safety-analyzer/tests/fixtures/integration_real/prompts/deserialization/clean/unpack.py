import zipfile
from pathlib import Path


def unpack(archive_path, target):
    root = Path(target).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.namelist():
            destination = (root / member).resolve()
            if not destination.is_relative_to(root):
                raise ValueError(f"unsafe path in archive: {member}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(member))
