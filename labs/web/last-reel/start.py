"""Start from built images and synchronize the current flag digest."""
from scripts.control import start_or_reset

if __name__ == "__main__":
    start_or_reset(reset=False)
    print("Last Reel is ready at http://127.0.0.1:8080. Checker digest synchronized.")
