#!/usr/bin/env python3
"""
One-command QR-video -> repository pipeline.

Decodes a video of standard byte-mode QR codes (each payload is
"{seq}/{total}:{base64_chunk}"), reassembles the base64 in order, verifies the
SHA-256, decodes it to tar.xz, and extracts the repository.

    python decode.py [VIDEO] [--out DIR] [--sha EXPECTED_SHA] [--keep-going]

Defaults: VIDEO = ../qr_codes.mp4 (or ./qr_codes.mp4); writes
repo-snapshot.tar.xz, repo-snapshot.tar.xz.b64, and restored/ into --out (default: .).

Requires:  pip install opencv-python zxing-cpp numpy
"""
import sys, os, re, time, hashlib, base64, lzma, tarfile, argparse

DEFAULT_SHA = "bab1a635e192a34c75ce8c031a42acf02fdd0da2a474601c8f7ac53b22cd90cf"
PAYLOAD = re.compile(r'^(\d+)/(\d+):(.+)$', re.DOTALL)


def find_video(arg):
    if arg:
        return arg
    for cand in ("qr_codes.mp4", os.path.join("..", "qr_codes.mp4")):
        if os.path.exists(cand):
            return cand
    sys.exit("No video given and qr_codes.mp4 not found. Pass the path explicitly.")


def scan(video):
    import cv2, zxingcpp
    QR = zxingcpp.BarcodeFormat.QRCode
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"Could not open video: {video}")
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    chunks, total = {}, None
    t0 = time.time(); fi = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        for res in zxingcpp.read_barcodes(gray, formats=QR):
            m = PAYLOAD.match(res.text or "")
            if m:
                total = int(m.group(2))
                chunks.setdefault(int(m.group(1)), m.group(3))
        fi += 1
        if fi % 250 == 0:
            print(f"  frame {fi}/{n}  collected {len(chunks)}/{total}  ({time.time()-t0:.0f}s)", flush=True)
    cap.release()
    return chunks, total


def main():
    ap = argparse.ArgumentParser(description="Decode a QR-code video back into a repository.")
    ap.add_argument("video", nargs="?", help="path to the QR video (default: ../qr_codes.mp4)")
    ap.add_argument("--out", default=".", help="output directory (default: current dir)")
    ap.add_argument("--sha", default=DEFAULT_SHA, help="expected SHA-256 of the reassembled base64")
    ap.add_argument("--keep-going", action="store_true", help="write/extract even if SHA mismatches")
    args = ap.parse_args()

    video = find_video(args.video)
    os.makedirs(args.out, exist_ok=True)
    print(f"Scanning {video} ...")
    chunks, total = scan(video)

    if not total:
        sys.exit("No '{seq}/{total}:...' QR payloads found in the video.")
    missing = [i for i in range(1, total + 1) if i not in chunks]
    print(f"Collected {len(chunks)}/{total} chunks.")
    if missing:
        print(f"MISSING sequence numbers: {missing[:50]}{' ...' if len(missing) > 50 else ''}")
        sys.exit("Cannot reassemble with missing chunks. Re-scan (the source HTML loops).")

    b64 = "".join(chunks[i] for i in range(1, total + 1))
    sha = hashlib.sha256(b64.encode("ascii")).hexdigest()
    ok = (sha == args.sha)
    print(f"Reassembled {len(b64)} base64 chars.")
    print(f"SHA-256: {sha}")
    print(f"Expected: {args.sha}")
    print("SHA MATCH:", ok)
    if not ok and not args.keep_going:
        sys.exit("SHA mismatch -- aborting. Re-scan, or pass --keep-going to write anyway.")

    b64_path = os.path.join(args.out, "repo-snapshot.tar.xz.b64")
    xz_path = os.path.join(args.out, "repo-snapshot.tar.xz")
    restored = os.path.join(args.out, "restored")
    with open(b64_path, "w") as f:
        f.write(b64)
    raw = base64.b64decode(b64)
    with open(xz_path, "wb") as f:
        f.write(raw)
    # extract (cross-platform; no shell tar needed)
    import shutil
    if os.path.isdir(restored):
        shutil.rmtree(restored)
    os.makedirs(restored)
    with tarfile.open(fileobj=lzma.open(xz_path), mode="r|") as tar:
        try:
            tar.extractall(restored, filter="data")  # py>=3.12 path-traversal-safe
        except TypeError:
            tar.extractall(restored)
    nfiles = sum(len(fs) for _, _, fs in os.walk(restored))
    print(f"\nWrote {b64_path}")
    print(f"Wrote {xz_path} ({len(raw)} bytes)")
    print(f"Extracted {nfiles} files into {restored}/")
    print("Done." if ok else "Done (SHA did NOT match -- output may be incomplete).")


if __name__ == "__main__":
    main()
