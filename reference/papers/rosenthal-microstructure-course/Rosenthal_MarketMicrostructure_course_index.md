# Dale Rosenthal — Market Microstructure & Electronic Trading course

**Course page:** https://sites.google.com/site/dalerosenthal/teaching/market-microstructure
**Used in:** Ch 4 (Spreads), Ch 5 (Kyle / Glosten–Milgrom), Ch 6 (Impact), Ch 7 (Order flow)

All course materials are hosted on Google Drive. The pattern to convert a `drive.google.com/file/d/FILE_ID/view` URL to a direct download is:

`https://drive.google.com/uc?export=download&id=FILE_ID`

## Course materials

### Syllabus
- https://drive.google.com/file/d/1zfumWYl93WIL2QT_Uc1mAt3D44udblcu/view

### Weekly slides (15 weeks)
| Week | URL |
|---|---|
| 1  | https://drive.google.com/file/d/1sumthGhscruBWee2J5tdTN4SKXMCYCmB/view |
| 2  | https://drive.google.com/file/d/13OgH3FNAPmqIjrQmHAD3XqbKuHptdNjv/view |
| 3  | https://drive.google.com/file/d/16r7G7RpgMI7kNyKuObjZwnkDnAbNZ6xe/view |
| 4  | https://drive.google.com/file/d/1U65bXWAKjlUobfddriNyE4kjy-_PW9rD/view |
| 5  | https://drive.google.com/file/d/1oMz1MH3zZY1f6463upIEgWfmz7lmQqnZ/view |
| 6  | https://drive.google.com/file/d/1nPZRCqMJKT9AeIlv-zLajXW18f-9MWa6/view |
| 7  | https://drive.google.com/file/d/1PWewNoCvDhQ7sIr7s3kHSQdFvypUXADz/view |
| 8  | https://drive.google.com/file/d/16dH4PPqA6EjrMYl9OopQqVmHIfCA2dTX/view |
| 9  | https://drive.google.com/file/d/1CnlvsblYGWlPTtvUWtkWe4WJNgqkx4rx/view |
| 10 | https://drive.google.com/file/d/1-q21B6PvCpHiGZvQXMRpqayv0UE2FebT/view |
| 11 | https://drive.google.com/file/d/1e5ECoMexJUOTVsLvZf2_1YhMTIDYV0kk/view |
| 14 | https://drive.google.com/file/d/1wIfPP_B-6TQfQgx2zzanW7L0svjZ9RdP/view |
| 15 | https://drive.google.com/file/d/1_SL3IRC1u-ol6v49wZ548uq2TrECQxgd/view |

*(Weeks 12 and 13 are not publicly posted — noted in bibliography as "embargoed".)*

### Homework and code
- Homework 1: https://drive.google.com/file/d/1DauSahjCzBSmIPhAHQX1JbmvS2Mh_JtO/view
- Glosten–Milgrom R code: https://drive.google.com/file/d/12egJwCTvqOM4ZNPYliIv8xYPm8SrkrXd/view
- Kyle R code: https://drive.google.com/file/d/1quAT-zBbafEzuybo-_x0U6nxAG5yCU3j/view
- Quote Delays R code: https://drive.google.com/file/d/18bNY7SW63W8bUbbqAEjQS7xPS5-RKXm9/view

## Downloading these

The slides are PDFs living on Google Drive. The auto-downloader may need to handle the "download anyway" confirmation page Google serves for larger files. If `curl` hits that page, the shell one-liner is:

```bash
FILE_ID="..."
curl -fLsSc cookies.txt "https://drive.google.com/uc?export=download&id=$FILE_ID" > /tmp/probe.html
CONFIRM=$(grep -oE 'confirm=[^&]+' /tmp/probe.html | head -1 | cut -d= -f2)
curl -fLsSb cookies.txt "https://drive.google.com/uc?export=download&confirm=$CONFIRM&id=$FILE_ID" -o out.pdf
```

Most small slide decks download fine without confirm.

## Notes for the PDF

- Rosenthal's Glosten–Milgrom R code is unusually valuable — it's one of the only publicly-available reference implementations. Use it to seed the Ch 5 worked numerical example.
- Weeks 2–4 likely cover spread theories and should be the primary source for Ch 4 and Ch 5.
- Weeks 5–7 likely cover order flow and impact — source for Ch 6, Ch 7.
