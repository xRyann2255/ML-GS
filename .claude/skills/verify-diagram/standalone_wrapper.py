# .claude/skills/verify-diagram/standalone_wrapper.py
"""Optional fast path: build a preview-cropped standalone PDF of ONE figure.
Falls back to whole-guide compile (caller's responsibility) if anything here fails."""
import re, os, argparse, subprocess

def _figure_env(tex, label):
    # the figure environment that contains \label{label}
    for m in re.finditer(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", tex, re.DOTALL):
        if ("\\label{%s}" % label) in m.group(1):
            return m.group(1)
    return None

def _balanced(s, start):
    # given index at '{', return index just after its matching '}'
    depth, i = 0, start
    while i < len(s):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(s)

def extract_figure_body(tex, label):
    env = _figure_env(tex, label)
    if env is None:
        raise ValueError("no figure with label %s" % label)
    m = re.search(r"\\(resizebox|scalebox)", env)
    if m:
        # consume macro + all its brace groups until one group holds the tikzpicture
        i = m.start()
        j = i
        body_end = i
        while j < len(env):
            b = env.find('{', j)
            if b == -1:
                break
            e = _balanced(env, b)
            body_end = e
            if "\\begin{tikzpicture}" in env[b:e]:
                break
            j = e
        return env[i:body_end].strip()
    # bare tikzpicture
    t0 = env.find("\\begin{tikzpicture}")
    t1 = env.find("\\end{tikzpicture}")
    if t0 == -1 or t1 == -1:
        raise ValueError("no tikzpicture in figure %s" % label)
    return env[t0:t1 + len("\\end{tikzpicture}")].strip()

def build_pdf(guide_dir, label, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    # find the chapter file containing the label
    chap = None
    for root, _, files in os.walk(os.path.join(guide_dir, "chapters")):
        for fn in files:
            if fn.endswith(".tex"):
                p = os.path.join(root, fn)
                with open(p, encoding="utf-8") as f:
                    if ("\\label{%s}" % label) in f.read():
                        chap = p
                        break
        if chap:
            break
    if not chap:
        raise ValueError("label %s not found under %s/chapters" % (label, guide_dir))
    with open(chap, encoding="utf-8") as f:
        body = extract_figure_body(f.read(), label)
    wrapper = (
        "\\documentclass[11pt,a4paper]{report}\n"
        "\\usepackage[active,tightpage]{preview}\n"
        "\\input{preamble}\n"
        "\\setlength\\PreviewBorder{6pt}\n"
        "\\begin{document}\n\\begin{preview}\n" + body + "\n\\end{preview}\n\\end{document}\n"
    )
    wpath = os.path.join(guide_dir, "_diagstandalone.tex")
    with open(wpath, "w", encoding="utf-8") as f:
        f.write(wrapper)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "_diagstandalone.tex"],
                       cwd=guide_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(guide_dir, "_diagstandalone.pdf")
    if r.returncode != 0 or not os.path.exists(pdf):
        raise RuntimeError("standalone compile failed; caller should fall back to whole-guide")
    return pdf

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--guide", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        print(build_pdf(a.guide, a.label, a.out))
        return 0
    except Exception as e:
        print("FALLBACK: %s" % e)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
