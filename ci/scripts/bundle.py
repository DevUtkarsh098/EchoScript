"""Extract only regular frontend assets from a verified, bounded release archive."""
import hashlib
import tarfile
from pathlib import Path, PurePosixPath


def extract(bundle, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(bundle, 'r:gz') as archive:
        members = archive.getmembers()
        if sum(item.size for item in members) > 100_000_000:
            raise ValueError('Oversized frontend bundle')
        for item in members:
            name = PurePosixPath(item.name)
            if name.is_absolute() or '..' in name.parts or not (item.isfile() or item.isdir()):
                raise ValueError('Unsafe frontend archive member')
        archive.extractall(destination, members=members, filter='data')
    if not (destination / 'index.html').is_file():
        raise ValueError('Frontend index missing')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == '__main__':
    import sys
    extract(sys.argv[1], sys.argv[2])
