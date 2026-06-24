# QR-video → repository decoder

Decodes a screen-recording of QR codes back into the original repository, and
verifies it against a known SHA-256.

Each QR is a standard byte-mode symbol whose payload is `"{seq}/{total}:{base64_chunk}"`.
The chunks are concatenated in sequence order to form one base64 string
(`repo-snapshot.tar.xz`, base64-encoded, no newlines), which must hash to:

```
bab1a635e192a34c75ce8c031a42acf02fdd0da2a474601c8f7ac53b22cd90cf
```

## One command

```bash
pip install opencv-python zxing-cpp numpy
python decode.py                 # uses ../qr_codes.mp4 by default
# or: python decode.py path/to/video.mp4 --out somedir
```

It scans every frame, reassembles the base64, verifies the SHA-256, decodes to
`repo-snapshot.tar.xz`, and extracts the repo into `restored/`. It aborts on a SHA
mismatch or any missing chunk (pass `--keep-going` to write output anyway).

Outputs (in `--out`, default the current dir):
- `repo-snapshot.tar.xz.b64` — the verified base64 string
- `repo-snapshot.tar.xz` — the decoded archive
- `restored/` — the extracted repository

## Files

| File | Purpose |
|---|---|
| `decode.py` | The decoder (one command, above). |
| `regenerate_qrs.py` | Source-side companion: regenerates standard, self-verified QR PNGs from the base64. Run on the machine that has the source file. |
| `repo-snapshot.tar.xz`, `.b64`, `restored/` | The recovered, SHA-verified output. |
