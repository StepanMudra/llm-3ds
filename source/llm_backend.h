// Common interface for the two llama2.c backends (fp32 run.c and int8 runq.c).
#pragma once

typedef struct {
    int dim, hidden_dim, n_layers, n_heads, vocab_size, seq_len;
    long file_bytes;
    long params;
} LlmInfo;

typedef struct {
    int (*load)(const char *model, const char *tokenizer, LlmInfo *info);  // 0 = ok
    void (*generate)(const char *prompt, int steps, float temperature, unsigned long long seed);
    void (*unload)(void);
    double (*tok_s)(void);
    int (*tokens)(void);
    const char *name;
} LlmBackend;

extern const LlmBackend llm_fp32, llm_q80;

// called instead of exit() inside llama2.c: jumps back to the menu
void llm_fail(void) __attribute__((noreturn));

// called after every generated token: shows the text and lets B stop the run
int llm_token_hook(void);
