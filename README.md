# LLM on Nintendo 3DS

A real Llama-architecture language model running **fully offline on an original Nintendo 3DS (2011)**:
ARM11 at 268 MHz, 128 MB RAM (~64 MB available to apps), no vector instructions.

Built on [llama2.c](https://github.com/karpathy/llama2.c) by Andrej Karpathy, with the
[TinyStories](https://arxiv.org/abs/2305.07759) models from
[karpathy/tinyllamas](https://huggingface.co/karpathy/tinyllamas). These models continue
simple English children's stories – they are not chatbots.

## Results (original 3DS)

| Model | Params | Format | Size | Speed |
|---|---|---|---|---|
| stories260K | 0.26 M | fp32 | 1 MB | **38.6 tokens/s** |
| stories260K | 0.26 M | int8 | 0.27 MB | breaks into gibberish – int8 hurts tiny models |
| stories15M | 15 M | int8 | 17 MB | _to be measured_ |
| stories42M | 42 M | int8 | 44 MB | _to be measured_ (edge of the memory limit) |
| stories15M | 15 M | fp32 | 60 MB | does not fit – shows "Could not load" |

The same code runs at ~10,000 tokens/s on an Apple M4 (one core).

## Features
- Model picker: every `*.bin` in `sdmc:/3ds/LLM3DS/` (fp32 or int8, detected automatically).
- System keyboard: type the start of a story, the model continues it.
- Tokens are printed as they are generated; speed and free RAM on the bottom screen.

| Button | Action |
|---|---|
| Up/Down + A | choose and load a model |
| A | new story (sampled, temperature 1.0) |
| X | greedy story (temperature 0, always the same) |
| Y | type your own start |
| L / R | length 32 / 64 / 128 / 256 tokens |
| B | stop generating |
| SELECT | back to the model list |
| START | exit |

## Build
Requires [devkitPro](https://devkitpro.org/) with `3ds-dev` (devkitARM + libctru).

```sh
export DEVKITPRO=/opt/devkitpro DEVKITARM=/opt/devkitpro/devkitARM
make            # -> LLM3DS.3dsx
```

## Models
Download from [karpathy/tinyllamas](https://huggingface.co/karpathy/tinyllamas):
`stories260K/stories260K.bin`, `stories260K/tok512.bin`, `stories15M.bin`, `stories42M.bin`,
and `tokenizer.bin` from llama2.c (rename it to `tok32000.bin`).

Quantize to int8 (no PyTorch or NumPy needed):

```sh
python3 tools/quantize_q80.py stories15M.bin stories15M_q80.bin
```

SD card layout:

```
/3ds/LLM3DS.3dsx
/3ds/LLM3DS/stories260K.bin
/3ds/LLM3DS/stories15M_q80.bin
/3ds/LLM3DS/stories42M_q80.bin
/3ds/LLM3DS/tok512.bin       # tokenizer for vocab 512
/3ds/LLM3DS/tok32000.bin     # tokenizer for vocab 32000
```

Launch through the Homebrew Launcher.

## What had to change for the 3DS
- `mmap` replaced by `malloc` + `fread`; timing via `osGetTime()`.
- Both llama2.c backends (`run.c` fp32, `runq.c` int8) in one binary; every global symbol is
  prefixed (`source/rename_*.h`).
- libctru gives half of app memory to the linear heap by default; it is shrunk to 6 MB so
  `malloc()` gets ~58 MB for weights.
- Context capped at 256 tokens (KV cache of stories42M: ~34 MB → ~8 MB).
- int8 token embeddings are dequantized per row instead of into a 37 MB float table.
- A failed load returns to the menu (`exit()` inside llama2.c jumps back via `longjmp`).

## Credits and licenses
- llama2.c © Andrej Karpathy, MIT – see `LICENSE.llama2c`.
- TinyStories dataset: Eldan & Li, 2023. Model weights are not included in this repository.
