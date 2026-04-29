"""
One-time utility: unzip Binance monthly 1m CSV zips and place them in data/
Usage:  python load_data.py BTCUSDT-1m-2025-*.zip
"""
import glob, os, sys, zipfile

def main():
    patterns = sys.argv[1:] if len(sys.argv) > 1 else ["*.zip"]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    if not files:
        print("No zip files found. Pass paths as arguments or run from the directory containing the zips.")
        sys.exit(1)

    os.makedirs("data", exist_ok=True)
    for f in sorted(files):
        print(f"Extracting {f}…")
        with zipfile.ZipFile(f) as z:
            z.extractall("data/")
    print(f"\nDone. CSV files are in ./data/")
    print("Now run:  python backtest_v4.py")

if __name__ == "__main__":
    main()
