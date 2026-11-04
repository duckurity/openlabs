"""Start built ParcelPoint images and synchronize both stage digests."""
from scripts.control import start_or_reset

if __name__ == '__main__':
    start_or_reset(reset=False)
    print('ParcelPoint is ready at http://127.0.0.1:8080. Both checker digests synchronized.')
