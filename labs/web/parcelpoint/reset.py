"""Reset only this ParcelPoint instance without pulling or rebuilding."""
from scripts.control import start_or_reset

if __name__ == '__main__':
    start_or_reset(reset=True)
    print('ParcelPoint reset complete. Accounts, sessions, codes and both flags rotated.')
