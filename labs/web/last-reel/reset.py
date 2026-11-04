"""Reset only this Last Reel instance; never build or pull images."""
from scripts.control import start_or_reset

if __name__ == "__main__":
    start_or_reset(reset=True)
    print("Last Reel reset complete. Public seed restored and checker digest rotated.")
