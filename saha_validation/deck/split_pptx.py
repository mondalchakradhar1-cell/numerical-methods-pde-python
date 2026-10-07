import sys, os, re, shutil, zipfile, subprocess, posixpath
src, outdir, prefix = sys.argv[1:4]
LIM = 27.5 * 2**20
z = zipfile.ZipFile(src)
names = z.namelist()
pres = z.read("ppt/presentation.xml").decode()
prels = z.read("ppt/_rels/presentation.xml.rels").decode()
rid2t = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', prels)) | {a: b for b, a in re.findall(r'Target="([^"]+)"[^>]*Id="(rId\d+)"', prels)}
ids = re.findall(r'<p:sldId id="(\d+)" r:id="(rId\d+)"/>', pres)
def slide_size(t):
    rel = "ppt/slides/_rels/" + os.path.basename(t) + ".rels"
    tot = z.getinfo("ppt/" + t).compress_size
    if rel in names:
        for m in set(re.findall(r'Target="\.\./media/([^"]+)"', z.read(rel).decode())):
            tot += z.getinfo("ppt/media/" + m).compress_size
    return tot
def is_appendix(t):
    x = z.read("ppt/" + t).decode()
    return "Appendix: every sheet" in x
sizes = [slide_size(rid2t[r]) for _, r in ids]
parts, cur, cs = [], [], 0
for i, (sid, r) in enumerate(ids):
    if cur and (cs + sizes[i] > LIM or is_appendix(rid2t[r])):
        parts.append(cur); cur, cs = [], 0
    cur.append(i); cs += sizes[i]
parts.append(cur)
for pi, keep in enumerate(parts):
    d = f"/tmp/claude-0/o2/split/u{pi}"
    shutil.rmtree(d, ignore_errors=True); z.extractall(d)
    keepids = {ids[i][0] for i in keep}
    x = pres
    x = re.sub(r'<p:sldId id="(\d+)" r:id="rId\d+"/>', lambda m: m.group(0) if m.group(1) in keepids else "", x)
    x = re.sub(r'<p14:sldId id="(\d+)"/>', lambda m: m.group(0) if m.group(1) in keepids else "", x)
    x = re.sub(r'<p14:section [^>]*>\s*<p14:sldIdLst>\s*</p14:sldIdLst>\s*</p14:section>', "", x)
    x = re.sub(r'<p14:section [^>]*>\s*<p14:sldIdLst/>\s*</p14:section>', "", x)
    open(d + "/ppt/presentation.xml", "w").write(x)
    subprocess.run([sys.executable, "/mnt/skills/public/pptx/scripts/clean.py", d], check=True, cwd="/mnt/skills/public/pptx/scripts", capture_output=True)
    out = os.path.join(outdir, f"{prefix}_part{pi+1}_slides{keep[0]+1}-{keep[-1]+1}.pptx")
    if os.path.exists(out): os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        zo.write(d + "/[Content_Types].xml", "[Content_Types].xml")
        for root, _, fs in os.walk(d):
            for f in fs:
                p = os.path.join(root, f); a = os.path.relpath(p, d)
                if a != "[Content_Types].xml": zo.write(p, a)
    print(out, len(keep), round(os.path.getsize(out) / 2**20, 1), "MiB")
