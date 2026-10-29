// LLM on Nintendo 3DS: Karpathy's llama2.c running a tiny Llama-architecture model.
// Top screen: generated story. Bottom screen: model info and speed.
#include <3ds.h>
#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>

#define TESTING  // skip llama2.c's command-line main()
#include "llama2_run.inc"

#define CHECKPOINT "romfs:/stories260K.bin"
#define TOKENIZER  "romfs:/tok512.bin"
#define STEPS      256

static PrintConsole top, bottom;

static void show_info(Transformer *t, int runs, double best) {
    consoleSelect(&bottom);
    consoleClear();
    Config *c = &t->config;
    printf("\x1b[1;1H  LLM on Nintendo 3DS (2011)\n");
    printf("  llama2.c by A. Karpathy\n\n");
    printf("  Model:  stories260K (Llama arch.)\n");
    printf("  Layers %d, dim %d, heads %d\n", c->n_layers, c->dim, c->n_heads);
    printf("  Vocab %d, context %d\n", c->vocab_size, c->seq_len);
    printf("  Weights: %ld KB in RAM\n\n", (long)(t->file_size / 1024));
    printf("  CPU: ARM11 268 MHz, 128 MB RAM\n");
    printf("  Offline, no network.\n\n");
    if (runs > 0) {
        printf("  Last run: %d tokens\n", g_tokens);
        printf("  Speed:    \x1b[32m%.1f tokens/s\x1b[0m\n", g_tok_s);
        printf("  Best:     %.1f tokens/s (%d runs)\n\n", best, runs);
    }
    printf("  Y: type your own start (keyboard)\n");
    printf("  A: new story   B: greedy story\n");
    printf("  START: exit\n");
    consoleSelect(&top);
}

int main(void) {
    gfxInitDefault();
    consoleInit(GFX_TOP, &top);
    consoleInit(GFX_BOTTOM, &bottom);
    consoleSelect(&top);

    Result rc = romfsInit();
    if (R_FAILED(rc)) printf("romfsInit failed: %08lX\n", rc);

    printf("Loading model...\n");
    Transformer transformer;
    build_transformer(&transformer, CHECKPOINT);
    Tokenizer tokenizer;
    build_tokenizer(&tokenizer, TOKENIZER, transformer.config.vocab_size);
    Sampler sampler;
    build_sampler(&sampler, transformer.config.vocab_size, 1.0f, 0.9f, osGetTime());

    static char prompt[128] = "Once upon a time";
    int runs = 0;
    double best = 0;
    consoleClear();
    printf("\x1b[33mPress A to tell a story.\x1b[0m\n");
    show_info(&transformer, runs, best);

    while (aptMainLoop()) {
        hidScanInput();
        u32 k = hidKeysDown();
        if (k & KEY_START) break;
        if (k & KEY_Y) {
            // classic 3DS software keyboard; the model continues whatever you type
            SwkbdState kb;
            char typed[128] = {0};
            swkbdInit(&kb, SWKBD_TYPE_NORMAL, 2, sizeof(typed) - 1);
            swkbdSetHintText(&kb, "Start of a story (English)");
            swkbdSetInitialText(&kb, prompt);
            if (swkbdInputText(&kb, typed, sizeof(typed)) == SWKBD_BUTTON_CONFIRM && typed[0]) {
                snprintf(prompt, sizeof(prompt), "%s", typed);
                k |= KEY_A;  // generate right away
            }
        }
        if (k & (KEY_A | KEY_B)) {
            consoleClear();
            sampler.temperature = (k & KEY_B) ? 0.0f : 1.0f;
            sampler.rng_state = osGetTime();
            generate(&transformer, &tokenizer, &sampler, prompt, STEPS);
            runs++;
            if (g_tok_s > best) best = g_tok_s;
            show_info(&transformer, runs, best);
        }
        gfxFlushBuffers();
        gfxSwapBuffers();
        gspWaitForVBlank();
    }

    free_sampler(&sampler);
    free_tokenizer(&tokenizer);
    free_transformer(&transformer);
    romfsExit();
    gfxExit();
    return 0;
}
