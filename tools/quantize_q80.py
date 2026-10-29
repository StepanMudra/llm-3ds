"""Convert a llama2.c fp32 checkpoint (legacy version 0) to the Q8_0 int8 format
(version 2) read by runq.c, without PyTorch or NumPy.

Mirrors version2_export() in llama2.c/export.py: rmsnorm weights stay fp32,
all matrices are quantized to symmetric int8 in groups (scale = max|w| / 127).

Usage: python3 quantize_q80.py IN_fp32.bin OUT_q80.bin [group_size=64]
"""
import struct
import sys
from array import array


def main():
    src, dst = sys.argv[1], sys.argv[2]
    gs = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    f = open(src, "rb")
    dim, hidden, n_layers, n_heads, n_kv, vocab, seq = struct.unpack("7i", f.read(28))
    shared = vocab > 0
    vocab = abs(vocab)
    head = dim // n_heads
    while dim % gs:
        gs //= 2
        print(f"BACKOFF: group size {gs}")

    def read(n):
        a = array("f")
        a.fromfile(f, n)
        return a

    # fp32 layout, see memory_map_weights() in run.c
    L = n_layers
    tok = read(vocab * dim)
    rms_att = read(L * dim)
    wq = read(L * dim * n_heads * head)
    wk = read(L * dim * n_kv * head)
    wv = read(L * dim * n_kv * head)
    wo = read(L * n_heads * head * dim)
    rms_ffn = read(L * dim)
    w1 = read(L * dim * hidden)
    w2 = read(L * hidden * dim)
    w3 = read(L * dim * hidden)
    rms_final = read(dim)
    read(seq * head // 2)  # legacy freq_cis_real
    read(seq * head // 2)  # legacy freq_cis_imag
    wcls = None if shared else read(vocab * dim)

    out = open(dst, "wb")
    out.write(struct.pack("I", 0x616B3432))
    out.write(struct.pack("i", 2))
    out.write(struct.pack("7i", dim, hidden, n_layers, n_heads, n_kv, vocab, seq))
    out.write(struct.pack("B", int(shared)))
    out.write(struct.pack("i", gs))
    out.write(b"\0" * (256 - out.tell()))
    for a in (rms_att, rms_ffn, rms_final):
        a.tofile(out)

    worst = 0.0

    def quant(w):
        nonlocal worst
        assert len(w) % gs == 0
        q, s = array("b"), array("f")
        for g in range(0, len(w), gs):
            grp = w[g:g + gs]
            scale = max(abs(x) for x in grp) / 127.0
            if scale == 0:
                q.extend([0] * gs)
            else:
                vals = [max(-127, min(127, round(x / scale))) for x in grp]
                q.extend(vals)
                worst = max(worst, max(abs(v * scale - x) for v, x in zip(vals, grp)))
            s.append(scale)
        q.tofile(out)
        s.tofile(out)

    def per_layer(a):
        n = len(a) // L
        return [a[i * n:(i + 1) * n] for i in range(L)]

    quant(tok)
    for t in (wq, wk, wv, wo, w1, w2, w3):
        for layer in per_layer(t):
            quant(layer)
    if wcls is not None:
        quant(wcls)
    out.close()
    print(f"{dst}: dim {dim}, layers {L}, vocab {vocab}, group {gs}, max group error {worst:.5f}")


if __name__ == "__main__":
    main()
