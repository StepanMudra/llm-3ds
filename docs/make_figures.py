import textwrap, html
W, H = 1280, 720
SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
BLUE, CRIT, GRAY = "#2a78d6", "#d03b3b", "#a3a29b"
SANS = "Helvetica Neue"
MONO = "Menlo"
e = html.escape

def svg(body, w=W, h=H, bg=SURF):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="8" height="8" fill="{GRAY}" opacity="0.35"/><line x1="0" y1="0" x2="0" y2="8" stroke="{GRAY}" stroke-width="3"/></pattern></defs>'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{body}</svg>')

def t(x, y, s, size=20, fill=INK, weight="normal", anchor="start", font=SANS):
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{e(s)}</text>'

def header(title, sub):
    return t(64, 84, title, 40, INK, "bold") + t(64, 122, sub, 21, INK2)

def footer(s="Měřeno na původním Nintendu 3DS (2011) · llama2.c (A. Karpathy) · modely TinyStories"):
    return t(64, H - 36, s, 16, MUTED)

def hbar(x, y, w, h, fill):
    # bar anchored left, 4px rounded data end only
    r = min(4, w / 2)
    if w <= 0: return ""
    return (f'<path d="M{x},{y} H{x+w-r} Q{x+w},{y} {x+w},{y+r} V{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} H{x} Z" fill="{fill}"/>')

# ---------- 1. speed ----------
rows = [("stories260K", "fp32 · 1 MB", 38.36, BLUE, "38,4 tok/s", "čitelný, ale jednoduchý text"),
        ("stories260K", "int8 · 0,27 MB", 47.23, "url(#hatch)", "47,2 tok/s", "rychlejší – ale text se rozpadne"),
        ("stories15M", "int8 · 17 MB", 1.54, BLUE, "1,54 tok/s", "souvislý příběh"),
        ("stories42M", "int8 · 44 MB", 0.68, BLUE, "0,68 tok/s", "nejlepší text, na hraně paměti"),
        ("stories15M", "fp32 · 60 MB", None, None, "", "")]
x0, xw, y0, bh, gap = 330, 640, 180, 50, 30
maxv = 50
b = header("Rychlost jazykového modelu na Nintendu 3DS", "Tokeny za sekundu · vyšší = rychlejší · stejný kód na Macu M4: ~10 000 tok/s")
for v in range(0, 51, 10):
    gx = x0 + xw * v / maxv
    b += f'<line x1="{gx}" y1="{y0-14}" x2="{gx}" y2="{y0 + 5*(bh+gap) - gap + 10}" stroke="{GRID}" stroke-width="1"/>'
    b += t(gx, y0 + 5*(bh+gap) - gap + 36, str(v), 16, MUTED, anchor="middle")
for i, (m, fmt, v, col, lab, note) in enumerate(rows):
    y = y0 + i * (bh + gap)
    b += t(x0 - 20, y + 22, m, 23, INK, "bold", "end") + t(x0 - 20, y + 45, fmt, 18, INK2, anchor="end")
    if v is None:
        b += f'<circle cx="{x0+16}" cy="{y+bh/2}" r="14" fill="{CRIT}"/>' + t(x0+16, y+bh/2+7, "✕", 18, "#ffffff", "bold", "middle")
        b += t(x0 + 42, y + bh/2 + 8, "nevejde se do paměti (malloc failed)", 22, INK, "bold")
        continue
    w = xw * v / maxv
    b += hbar(x0, y, max(w, 6), bh, col)
    b += t(x0 + max(w, 6) + 14, y + 22, lab, 22, INK, "bold") + t(x0 + max(w, 6) + 14, y + 45, note, 18, INK2)
b += footer()
open("01_rychlost_3ds.svg", "w").write(svg(b))

# ---------- 2. memory ----------
LIM = 59160 / 1024
mrows = [("stories260K", "int8", 644/1024, "0,6 MB", BLUE, "naměřeno"),
         ("stories260K", "fp32", 1402/1024, "1,4 MB", BLUE, "naměřeno"),
         ("stories15M", "int8", (59160-37579)/1024, "21,1 MB", BLUE, "naměřeno"),
         ("stories42M", "int8", (59160-6246)/1024, "51,7 MB", BLUE, "naměřeno – zbývá 6 MB"),
         ("stories15M", "fp32", 59390/1024 + 4.6, "> 64 MB", CRIT, "nevejde se")]
x0, xw, y0, bh, gap, maxv = 300, 760, 180, 50, 30, 70
b = header("Kolik paměti model potřebuje", "RAM obsazená modelem (váhy + pracovní paměť) · 3DS dá aplikaci jen ~58 MB")
for v in range(0, 71, 10):
    gx = x0 + xw * v / maxv
    b += f'<line x1="{gx}" y1="{y0-14}" x2="{gx}" y2="{y0+5*(bh+gap)-gap+10}" stroke="{GRID}" stroke-width="1"/>'
    b += t(gx, y0+5*(bh+gap)-gap+36, f"{v} MB" if v else "0", 16, MUTED, anchor="middle")
for i, (m, fmt, v, lab, col, note) in enumerate(mrows):
    y = y0 + i*(bh+gap)
    b += t(x0-20, y+22, m, 22, INK, "bold", "end") + t(x0-20, y+44, fmt, 18, INK2, anchor="end")
    w = xw * min(v, maxv) / maxv
    b += hbar(x0, y, max(w, 6), bh, col)
    tx = x0 + max(w, 6) + 14
    if w > xw * 0.5: tx = x0 + 14  # long bars: label inside, clear of the limit line
    fill = "#ffffff" if tx == x0 + 14 else INK
    b += t(tx, y+22, lab, 21, fill, "bold") + t(tx, y+44, note, 17, "#ffffff" if tx == x0+14 else INK2)
lx = x0 + xw * LIM / maxv
b += f'<line x1="{lx}" y1="{y0-30}" x2="{lx}" y2="{y0+5*(bh+gap)-gap+10}" stroke="{INK}" stroke-width="2" stroke-dasharray="6 5"/>'
b += t(lx, y0-38, "limit pro aplikaci ~58 MB", 18, INK, "bold", "middle")
b += footer()
open("02_pamet_3ds.svg", "w").write(svg(b))

# ---------- 3. quantization text comparison ----------
def card(x, y, w, h, title, sub, text, ok, cols=46):
    c = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#ffffff" stroke="{GRID}" stroke-width="2"/>'
    mark = (BLUE, "✓") if ok == 1 else ((CRIT, "✕") if ok == 0 else (GRAY, "!"))
    c += f'<circle cx="{x+34}" cy="{y+38}" r="14" fill="{mark[0]}"/>' + t(x+34, y+45, mark[1], 17, "#ffffff", "bold", "middle")
    c += t(x+60, y+46, title, 24, INK, "bold") + t(x+w-24, y+46, sub, 18, INK2, anchor="end")
    for j, line in enumerate(textwrap.wrap(text, cols)[:7]):
        c += t(x+28, y+92+j*28, line, 18, INK, font=MONO)
    return c
b = header("Kvantizace: malému modelu škodí, většímu pomůže", "Stejný model ve 32 bitech (fp32) a v 8 bitech (int8) · výstup přímo z 3DS")
cw, ch = 560, 290
b += card(64, 160, cw, ch, "stories260K · fp32", "1 MB · 38,4 tok/s",
          "Once upon a time, there was a little girl named Lily. She loved to play outside and eat whenever she could run on the pastries. One day, she found a big, able to hide in the park.", 1)
b += card(656, 160, cw, ch, "stories260K · int8", "0,27 MB · 47,2 tok/s",
          "Once upon a time, there there there there there there there there there there there … upon upon upon upon upon upon upon upon upon upon", 0)
b += card(64, 474, cw, 190, "stories15M · fp32", "60 MB",
          "malloc failed (60816028 bytes) – Could not load this model. The 3DS has only ~64 MB for apps.", 0)
b += card(656, 474, cw, 190, "stories15M · int8", "17 MB · 1,54 tok/s",
          "Once upon a time, in a small village, there lived a boy named Tim. Tim was a very alert boy who always watched out for danger.", 1)
open("03_kvantizace.svg", "w").write(svg(b, H=720) if False else svg(b))

# ---------- 4. clean 3DS screens ----------
TOPC, BOTC = 60, 40
def screens(name, top_lines, bottom_lines, caption):
    sw, sh, bw = 800, 480, 640
    w, h = 1000, 1180
    b = t(w/2, 62, caption, 30, INK, "bold", "middle")
    # top screen
    tx, ty = (w - sw) / 2, 96
    b += f'<rect x="{tx-18}" y="{ty-18}" width="{sw+36}" height="{sh+36}" rx="22" fill="#1d6f8a"/>'
    b += f'<rect x="{tx}" y="{ty}" width="{sw}" height="{sh}" fill="#000000"/>'
    for j, (line, col) in enumerate(top_lines[:20]):
        b += t(tx+12, ty+30+j*23, line, 21, col, font=MONO)
    bx, by = (w - bw) / 2, ty + sh + 70
    b += f'<rect x="{bx-18}" y="{by-18}" width="{bw+36}" height="{sh+36}" rx="22" fill="#1d6f8a"/>'
    b += f'<rect x="{bx}" y="{by}" width="{bw}" height="{sh}" fill="#000000"/>'
    for j, (line, col) in enumerate(bottom_lines[:20]):
        b += t(bx+12, by+30+j*23, line, 21, col, font=MONO)
    open(name, "w").write(svg(b, w, h))

WH, GR, YE, RE = "#e8e8e8", "#3fdc5a", "#f2d23c", "#ff6a5a"
def wrapc(s, n=TOPC):
    out = []
    for para in s.split("\n"):
        out += [para[i:i+n] for i in range(0, max(len(para), 1), n)]  # console wraps mid-word, like on the device
    return [(l, WH) for l in out]
def info(model, params, layers, vocab, kb, free, tokens, speed):
    L = [("  LLM on Nintendo 3DS (2011)", WH), ("", WH), (f"  Model: {model}", WH), (f"  ~{params}", WH),
         (f"  {layers}", WH), (f"  {vocab}", WH), (f"  Weights: {kb} KB in RAM", WH),
         (f"  RAM for models: {free} / 59160 KB free", WH), ("  CPU: ARM11 268 MHz, offline", WH), ("", WH)]
    if tokens:
        L += [(f"  Last run: {tokens} tokens", WH), (f"  Speed:    {speed} tokens/s", GR), (f"  Best:     {speed} tokens/s (1 runs)", WH), ("", WH)]
    L += [("  Y: type start  A: story  X: greedy", WH), ("  L/R: length tokens", WH), ("  B: stop  SELECT: models  START: exit", WH)]
    return L

screens("04_obrazovka_260K_fp32.svg",
        wrapc("Once upon a time, there was a little girl named Lily. She loved to play outside and eat whenever she could run on the pastries. One day, she found a big, able to hide in the park. She was so pretty and she started to spray to the wall. She thought it was a good ending and it made a better salad for her cup.\nWhen Lily's dad came home, she went to the farm. She wanted to take a nap. Her dad said, \"Max, why are you okay?\" Lily felt sad and confused. Lily smiled and said, \"I don't want to go home! You makes my pretty test and you can share it.\" She was"),
        info("stories260K.bin", "0.26 M params, fp32", "Layers 5, dim 64, heads 8", "Vocab 512, context 256", 1031, 57758, 256, "38.36"),
        "stories260K · fp32 · 38,4 tokenu/s")
screens("05_obrazovka_260K_int8.svg",
        wrapc("Once upon a time, " + "there " * 62 + "upon " * 185),
        info("stories260K_q80.bin", "0.26 M params, int8 (Q8_0)", "Layers 5, dim 64, heads 8", "Vocab 512, context 256", 272, 58516, 256, "47.23"),
        "stories260K · int8 · 47,2 tokenu/s – rozbitý")
screens("06_obrazovka_15M_int8.svg",
        wrapc("Once upon a time, in a small village, there lived a boy named Tim. Tim was a very alert boy who always watched out for danger. One day, Tim saw a big rock in his way. He wanted to move it, but it was too heavy for him.\nTim asked his friend, Sam,"),
        info("stories15M_q80.bin", "15.19 M params, int8 (Q8_0)", "Layers 6, dim 288, heads 6", "Vocab 32000, context 256", 16700, 37579, 64, "1.54"),
        "stories15M · int8 · 1,54 tokenu/s")
menu = [("  LLM on Nintendo 3DS (2011)", WH), ("  llama2.c by A. Karpathy", WH), ("", WH), ("  Choose a model:", WH), ("", WH),
        ("   stories260K.bin       1031 KB fp32", WH), ("   stories260K_q80.bin    272 KB int8", WH),
        ("   stories42M_q80.bin   43282 KB int8", WH), ("   stories15M_q80.bin   16700 KB int8", WH),
        (" > stories15M.bin       59390 KB fp32", GR), ("", WH), ("  RAM for models: 59143 / 59160 KB free", WH), ("", WH),
        ("  Up/Down: choose   A: load", WH), ("  START: exit", WH)]
screens("07_obrazovka_42M_int8.svg",
        wrapc("Once upon a time, there was a little girl named Lily. She loved to sing and dance, but she was too scared to perform in front of her friends. One day, her friend Timmy came to her house and asked her why she looked so sad.\nLily replied, \"I want to"),
        info("stories42M_q80.bin", "41.68 M params, int8 (Q8_0)", "Layers 8, dim 512, heads 8", "Vocab 32000, context 256", 43282, 6246, 64, "0.68"),
        "stories42M · int8 · 0,68 tokenu/s")
screens("08_obrazovka_15M_fp32_nevejde.svg",
        [("Loading stories15M.bin (59390 KB)...", WH), ("malloc failed (60816028 bytes)", WH), ("", WH),
         ("Could not load this model.", RE), ("The 3DS has only ~64 MB for apps.", WH), ("Press A to go back.", WH)],
        menu, "stories15M · fp32 · 60 MB se nevejde")
print("ok")
