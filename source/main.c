// LLM on Nintendo 3DS: Karpathy's llama2.c with a model picker.
// Models (*.bin) and tokenizers (tok<vocab>.bin or tokenizer.bin) live on the SD card in
// /3ds/LLM3DS/. Both fp32 checkpoints and int8 (Q8_0, "ak42") checkpoints are supported.
#include <3ds.h>
#include <dirent.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include "llm_backend.h"

#include <malloc.h>

// libctru splits app memory 50/50 between the linear heap (GPU/system buffers) and malloc().
// Model weights need malloc(), so keep the linear heap small (framebuffers + keyboard fit easily).
u32 __ctru_linear_heap_size = 6 * 1024 * 1024;

#define MODEL_DIR "sdmc:/3ds/LLM3DS/"
#define MAX_MODELS 16

typedef struct {
    char file[64];
    long bytes;
    int int8;
} Entry;

static PrintConsole top, bottom;
static Entry models[MAX_MODELS];
static int n_models;
static jmp_buf on_fail;
static int stop_requested;

void llm_fail(void) { longjmp(on_fail, 1); }

int llm_token_hook(void) {
    gfxFlushBuffers();
    gfxSwapBuffers();
    hidScanInput();
    if (hidKeysDown() & KEY_B) {
        stop_requested = 1;
        longjmp(on_fail, 2);
    }
    return 0;
}

static void scan_models(void) {
    n_models = 0;
    DIR *d = opendir(MODEL_DIR);
    if (!d) return;
    struct dirent *e;
    while ((e = readdir(d)) && n_models < MAX_MODELS) {
        size_t n = strlen(e->d_name);
        if (n < 5 || e->d_name[0] == '.' || strcmp(e->d_name + n - 4, ".bin") || !strncmp(e->d_name, "tok", 3)) continue;
        Entry *m = &models[n_models];
        snprintf(m->file, sizeof(m->file), "%s", e->d_name);
        char path[128];
        snprintf(path, sizeof(path), MODEL_DIR "%s", m->file);
        struct stat st;
        m->bytes = stat(path, &st) ? 0 : (long)st.st_size;
        unsigned magic = 0;
        FILE *f = fopen(path, "rb");
        if (f) { fread(&magic, 4, 1, f); fclose(f); }
        m->int8 = magic == 0x616b3432;
        n_models++;
    }
    closedir(d);
}

static void tokenizer_for(int vocab, char *out, size_t size) {
    snprintf(out, size, MODEL_DIR "tok%d.bin", vocab);
    struct stat st;
    if (stat(out, &st)) snprintf(out, size, MODEL_DIR "tokenizer.bin");
}

static int vocab_of(const char *path, int int8) {
    int cfg[7] = {0};
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    if (int8) fseek(f, 8, SEEK_SET);
    fread(cfg, sizeof(int), 7, f);
    fclose(f);
    return abs(cfg[5]);
}

static void free_ram_line(void) {
    extern u32 __ctru_heap_size;
    unsigned long used = (unsigned long)mallinfo().uordblks;
    printf("  RAM for models: %lu / %lu KB free\n", (unsigned long)(__ctru_heap_size - used) / 1024,
           (unsigned long)__ctru_heap_size / 1024);
}

static int pick_model(int sel) {
    int dirty = 1;  // redraw only after a key press; clearing every frame tears the console
    while (aptMainLoop()) {
        if (!dirty) goto input;
        dirty = 0;
        consoleSelect(&bottom);
        consoleClear();
        printf("\x1b[1;1H  LLM on Nintendo 3DS (2011)\n");
        printf("  llama2.c by A. Karpathy\n\n");
        printf("  Choose a model:\n\n");
        if (!n_models) printf("  No models in " MODEL_DIR "\n");
        for (int i = 0; i < n_models; i++)
            printf("%s %-20.20s %5ld KB %s\x1b[0m\n", i == sel ? "\x1b[32m >" : "  ", models[i].file,
                   models[i].bytes / 1024, models[i].int8 ? "int8" : "fp32");
        printf("\n");
        free_ram_line();
        printf("\n  Up/Down: choose   A: load\n  START: exit\n");
    input:
        gfxFlushBuffers();
        gfxSwapBuffers();
        gspWaitForVBlank();
        hidScanInput();
        u32 k = hidKeysDown();
        if (k & KEY_START) return -1;
        if (n_models && (k & KEY_DOWN)) { sel = (sel + 1) % n_models; dirty = 1; }
        if (n_models && (k & KEY_UP)) { sel = (sel + n_models - 1) % n_models; dirty = 1; }
        if (n_models && (k & KEY_A)) return sel;
    }
    return -1;
}

static void show_info(const Entry *m, const LlmBackend *b, const LlmInfo *in, int steps, int runs, double best) {
    consoleSelect(&bottom);
    consoleClear();
    printf("\x1b[1;1H  LLM on Nintendo 3DS (2011)\n\n");
    printf("  Model: %.30s\n", m->file);
    printf("  ~%.2f M params, %s\n", in->params / 1e6, b->name);
    printf("  Layers %d, dim %d, heads %d\n", in->n_layers, in->dim, in->n_heads);
    printf("  Vocab %d, context %d\n", in->vocab_size, in->seq_len);
    printf("  Weights: %ld KB in RAM\n", in->file_bytes / 1024);
    free_ram_line();
    printf("  CPU: ARM11 268 MHz, offline\n\n");
    if (runs > 0) {
        printf("  Last run: %d tokens\n", b->tokens());
        printf("  Speed:    \x1b[32m%.2f tokens/s\x1b[0m\n", b->tok_s());
        printf("  Best:     %.2f tokens/s (%d runs)\n\n", best, runs);
    }
    printf("  Y: type start  A: story  X: greedy\n");
    printf("  L/R: length %d tokens\n", steps);
    printf("  B: stop  SELECT: models  START: exit\n");
    consoleSelect(&top);
}

int main(void) {
    gfxInitDefault();
    consoleInit(GFX_TOP, &top);
    consoleInit(GFX_BOTTOM, &bottom);
    scan_models();

    static char prompt[128] = "Once upon a time";
    static const int lengths[] = {32, 64, 128, 256};
    int sel = 0;

    while ((sel = pick_model(sel)) >= 0) {
        Entry *m = &models[sel];
        const LlmBackend *b = m->int8 ? &llm_q80 : &llm_fp32;
        char path[128], tok[128];
        snprintf(path, sizeof(path), MODEL_DIR "%s", m->file);
        tokenizer_for(vocab_of(path, m->int8), tok, sizeof(tok));

        consoleSelect(&top);
        consoleClear();
        printf("Loading %s (%ld KB)...\n", m->file, m->bytes / 1024);
        gfxFlushBuffers();
        gfxSwapBuffers();

        LlmInfo info;
        if (setjmp(on_fail)) {
            b->unload();
            printf("\n\x1b[31mCould not load this model.\x1b[0m\n");
            printf("The 3DS has only ~64 MB for apps.\nPress A to go back.\n");
            while (aptMainLoop()) {
                gfxFlushBuffers(); gfxSwapBuffers(); gspWaitForVBlank();
                hidScanInput();
                if (hidKeysDown() & KEY_A) break;
            }
            continue;
        }
        b->load(path, tok, &info);

        int li = info.params > 5000000 ? 1 : 3;  // big models: shorter default stories
        int runs = 0;
        double best = 0;
        consoleClear();
        printf("\x1b[33mPress A for a story, Y to type a start.\x1b[0m\n");
        show_info(m, b, &info, lengths[li], runs, best);

        volatile int back = 0;
        while (!back && aptMainLoop()) {
            hidScanInput();
            u32 k = hidKeysDown();
            if (k & KEY_START) { b->unload(); goto out; }
            if (k & KEY_SELECT) back = 1;
            if (k & KEY_R) { li = (li + 1) % 4; show_info(m, b, &info, lengths[li], runs, best); }
            if (k & KEY_L) { li = (li + 3) % 4; show_info(m, b, &info, lengths[li], runs, best); }
            if (k & KEY_Y) {
                // classic 3DS software keyboard; the model continues whatever you type
                SwkbdState kb;
                char typed[128] = {0};
                swkbdInit(&kb, SWKBD_TYPE_NORMAL, 2, sizeof(typed) - 1);
                swkbdSetHintText(&kb, "Start of a story (English)");
                swkbdSetInitialText(&kb, prompt);
                if (swkbdInputText(&kb, typed, sizeof(typed)) == SWKBD_BUTTON_CONFIRM && typed[0]) {
                    snprintf(prompt, sizeof(prompt), "%s", typed);
                    k |= KEY_A;
                }
            }
            if (k & (KEY_A | KEY_X)) {
                consoleClear();
                stop_requested = 0;
                if (!setjmp(on_fail)) b->generate(prompt, lengths[li], (k & KEY_X) ? 0.0f : 1.0f, osGetTime());
                else printf("\n\x1b[33m[stopped]\x1b[0m\n");
                runs++;
                if (b->tok_s() > best) best = b->tok_s();
                show_info(m, b, &info, lengths[li], runs, best);
            }
            gfxFlushBuffers();
            gfxSwapBuffers();
            gspWaitForVBlank();
        }
        b->unload();
    }
out:
    gfxExit();
    return 0;
}
