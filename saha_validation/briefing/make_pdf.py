#!/usr/bin/env python3
"""Fill the tables of briefing_src.html and print it to SAHA_briefing_notes.pdf with headless Chromium."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(sys.argv[1]))
s = open(os.path.join(HERE, "briefing_src.html")).read()
for k, v in T.items():
    s = s.replace("{{" + k + "}}", v)
html = os.path.join(HERE, "briefing.html")
open(html, "w").write(s)
pdf = os.path.join(HERE, "SAHA_briefing_notes.pdf")
subprocess.run(["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", "file://" + html], check=True, capture_output=True)
print(pdf)
