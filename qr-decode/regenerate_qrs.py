"""
Regenerate the QR-code series CORRECTLY (run on the SOURCE machine).

Why this is needed: the original qr_codes.mp4 used a non-standard QR encoder
(invalid format-information bits + each data codeword repeated ~8x). No standard
scanner can read those, and the payload was corrupted past chunk 1, so the file
was unrecoverable from the video. This script produces STANDARD QR codes that any
scanner can read, and verifies every single QR round-trips before you use it.

Requires:  pip install qrcode pillow zxing-cpp numpy
"""
import hashlib, qrcode, qrcode.util as u
from qrcode.constants import ERROR_CORRECT_M
import zxingcpp, numpy as np

TARGET = "bab1a635e192a34c75ce8c031a42acf02fdd0da2a474601c8f7ac53b22cd90cf"

# 1) Load the base64 EXACTLY as hashed: no newlines, no trailing newline.
b64 = open("repo-snapshot.tar.xz.b64").read().strip()
sha = hashlib.sha256(b64.encode("ascii")).hexdigest()
print("source SHA-256:", sha)
assert sha == TARGET, "SHA mismatch on the source base64 itself!"

# 2) Split into pieces. ~1000 chars/piece -> ~v20 byte-mode QR, stays crisp on video.
PIECE = 1000
pieces = [b64[i:i + PIECE] for i in range(0, len(b64), PIECE)]
total = len(pieces)
print("total chunks:", total)

# 3) Generate STANDARD QRs and VERIFY each one decodes back before saving.
for seq, piece in enumerate(pieces, 1):
    payload = f"{seq}/{total}:{piece}"
    q = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=8, border=4)
    q.add_data(u.QRData(payload.encode(), mode=u.MODE_8BIT_BYTE))  # force byte mode
    q.make(fit=True)
    img = q.make_image().convert("L")
    res = zxingcpp.read_barcodes(np.array(img))
    assert res and res[0].text == payload, f"chunk {seq} did NOT round-trip -- aborting"
    img.save(f"qr_{seq:04d}.png")

print(f"All {total} chunks generated AND verified decodable. Reassembly check:")
# 4) Final sanity: reassemble straight from the payloads and re-hash.
reasm = "".join(pieces)
assert hashlib.sha256(reasm.encode()).hexdigest() == TARGET
print("  reassembly SHA matches. Safe to build the video from qr_*.png.")
