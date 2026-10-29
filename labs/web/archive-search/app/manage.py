"""Run only as the operator. Stop web workers before resetting."""

import argparse
from pathlib import Path

import seed
from app import config


def reset():
    # All targets are fixed filenames below DATA_DIR. No recursive deletion.
    root = Path(config.DATA_DIR).resolve()
    for name in ("auth.sqlite", "catalog.sqlite"):
        for suffix in ("", "-journal", "-wal", "-shm"):
            target = root / (name + suffix)
            if target.is_symlink():
                raise RuntimeError("Refusing to reset symlinked database files")
            target.unlink(missing_ok=True)
    seed.main()
    print("Reset complete. Sessions revoked; catalog restored; submission flag restored.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "reset"))
    args = parser.parse_args()
    if args.command == "reset":
        reset()
    else:
        seed.main()


if __name__ == "__main__":
    main()
