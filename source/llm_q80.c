// int8 (Q8_0) backend: llama2.c code with every global symbol prefixed by "q80_".
#include <3ds.h>
#include <stdio.h>
#include <stdlib.h>
#include "llm_backend.h"
#include "rename_q80.h"
#define TESTING
#define exit(code) llm_fail()
#define fflush(stream) llm_token_hook()  // called by generate() after every token
#include "llama2q_run.inc"
#undef exit
#undef fflush

static Transformer T;
static Tokenizer K;
static Sampler S;
static int loaded;

static int load(const char *model, const char *tok, LlmInfo *info) {
    build_transformer(&T, (char *)model);
    build_tokenizer(&K, (char *)tok, T.config.vocab_size);
    build_sampler(&S, T.config.vocab_size, 1.0f, 0.9f, 1);
    loaded = 1;
    Config *c = &T.config;
    long kv = (long)c->dim * c->n_kv_heads / c->n_heads;
    *info = (LlmInfo){c->dim, c->hidden_dim, c->n_layers, c->n_heads, c->vocab_size, c->seq_len,
                      (long)T.file_size,
                      (long)c->vocab_size * c->dim + (long)c->n_layers *
                          (2L * c->dim * c->dim + 2L * c->dim * kv + 3L * c->dim * c->hidden_dim)};
    return 0;
}

static void gen(const char *prompt, int steps, float temperature, unsigned long long seed) {
    S.temperature = temperature;
    S.rng_state = seed;
    generate(&T, &K, &S, (char *)prompt, steps);
}

static void unload(void) {
    if (!loaded) return;
    free_sampler(&S);
    free_tokenizer(&K);
    free_transformer(&T);
    loaded = 0;
}

static double tok_s(void) { return g_tok_s; }
static int tokens(void) { return g_tokens; }

const LlmBackend llm_q80 = {load, gen, unload, tok_s, tokens, "int8 (Q8_0)"};
