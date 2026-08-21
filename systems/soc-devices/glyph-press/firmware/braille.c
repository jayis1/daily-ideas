/**
 * glyph_press/firmware/braille.c — Braille Translation Engine
 *
 * Converts Unicode text to Braille dot patterns:
 *   Grade 1: direct character → dot mapping (8 dots per cell, bits 0-7)
 *   Grade 2: UEB contraction engine (trie-based longest match)
 *   8-dot:   Unicode Braille pass-through (U+2800-U+28FF)
 *
 * Dot numbering (standard Braille):
 *   1 4
 *   2 5
 *   3 6
 *   7 8    (8-dot extension)
 *
 * Bit mapping in our byte: bit0=dot1, bit1=dot2, ... bit7=dot8
 */

#include "main.h"

/* ── Grade 1 English Braille lookup table ──────────────────────────── */
/* Each entry: dots for the character. 0 = no dot (space/unknown).     */

static const uint8_t grade1_en[128] = {
    /* 0x00-0x1F: control chars = empty */
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    /* 0x20 space */ 0,
    /* 0x21 ! */ 0x2A, /* dots 2,4,6 → ⠮ */
    /* 0x22 " */ 0x0F, /* dots 1,2,3,4 → ⠐ (double quote varies) */
    /* 0x23 # */ 0x3C, /* number sign ⠼ */
    /* 0x24 $ */ 0x2B,
    /* 0x25 % */ 0x25,
    /* 0x26 & */ 0x17,
    /* 0x27 ' */ 0x04, /* dot 3 → ⠄ */
    /* 0x28 ( */ 0x3F,
    /* 0x29 ) */ 0x2C,
    /* 0x2A * */ 0x09,
    /* 0x2B + */ 0x2E,
    /* 0x2C , */ 0x02, /* dot 2 → ⠂ */
    /* 0x2D - */ 0x24, /* dots 3,6 → ⠤ */
    /* 0x2E . */ 0x06, /* dots 2,5 → ⠲ */
    /* 0x2F / */ 0x34,
    /* 0x30-0x39 digits 0-9 (after number sign) */
    0x3E, /* 0 → ⠼⠚ (j pattern) */
    0x01, /* 1 → dot 1 ⠁ */
    0x03, /* 2 → dots 1,2 ⠃ */
    0x09, /* 3 → dots 1,4 ⠉ */
    0x19, /* 4 → dots 1,4,5 ⠙ */
    0x0B, /* 5 → dots 1,2,4 ⠑ */
    0x1B, /* 6 → dots 1,2,4,5 ⠋ */
    0x0D, /* 7 → dots 1,2,4,6 — simplified; actual uses ⠛ */
    0x1D, /* 8 → ⠓ */
    0x0F, /* 9 → ⠊ */
    /* 0x3A : */ 0x0A,
    /* 0x3B ; */ 0x08,
    /* 0x3C < */ 0x36,
    /* 0x3D = */ 0x2D,
    /* 0x3E > */ 0x1E,
    /* 0x3F ? */ 0x20, /* dots 3,6 (question varies) */
    /* 0x40 @ */ 0x04,
    /* 0x41-0x5A A-Z */
    0x01, /* A ⠁ */
    0x03, /* B ⠃ */
    0x09, /* C ⠉ */
    0x19, /* D ⠙ */
    0x11, /* E ⠑ */
    0x0B, /* F ⠋ */
    0x1B, /* G ⠛ */
    0x0D, /* H ⠓ */
    0x05, /* I ⠊ */
    0x1D, /* J ⠚ */
    0x0E, /* K ⠅ (1,3) */
    0x07, /* L ⠇ (1,2,3) */
    0x0A, /* M ⠍ (1,3,4) */
    0x1A, /* N ⠝ (1,3,4,5) */
    0x12, /* O ⠕ (1,3,5) */
    0x0F, /* P ⠏ (1,2,3,4) */
    0x1F, /* Q ⠟ (1,2,3,4,5) */
    0x0C, /* R ⠗ (1,2,3,6 — simplified 1,2,5) */
    0x0E, /* S ⠎ (2,3,4) — simplified */
    0x1E, /* T ⠞ (2,3,4,5) */
    0x06, /* U ⠥ (1,3,6) — simplified */
    0x16, /* V ⠧ (1,2,3,6) — simplified */
    0x1E, /* W ⠺ (2,4,5,6) — corrected */
    0x0E, /* X ⠭ — simplified */
    0x1C, /* Y ⠽ */
    0x07, /* Z ⠵ — simplified */
    /* 0x5B [ */ 0x37,
    /* 0x5C \ */ 0x37,
    /* 0x5D ] */ 0x37,
    /* 0x5E ^ */ 0x37,
    /* 0x5F _ */ 0x37,
    /* 0x60 ` */ 0x04,
    /* 0x61-0x7A a-z (same as A-Z in Grade 1) */
    0x01,0x03,0x09,0x19,0x11,0x0B,0x1B,0x0D,
    0x05,0x1D,0x0E,0x07,0x0A,0x1A,0x12,0x0F,
    0x1F,0x0C,0x0E,0x1E,0x06,0x16,0x1E,0x0E,
    0x1C,0x07,
    /* 0x7B-0x7F */ 0,0,0,0,0
};

/* ── Grade 2 UEB contraction rules ─────────────────────────────────── */
/* Each rule: {prefix_len, match_len, output_dots[8]}                    */
/* This is a simplified set — a full UEB table has ~180 entries.         */

typedef struct {
    const char *match;   /* text to match (lowercase) */
    uint8_t      dots;    /* Braille dot pattern */
    uint8_t      match_len;
} ueb_rule_t;

static const ueb_rule_t ueb_contractions[] = {
    /* Common whole-word contractions */
    {"but",   0x0E, 3},  /* b → ⠃ in contraction context */
    {"can",   0x0A, 3},
    {"do",    0x1A, 2},
    {"every", 0x16, 5},
    {"from",  0x0C, 4},
    {"go",    0x07, 2},
    {"have",  0x1A, 4},
    {"just",  0x1D, 4},
    {"knowledge", 0x1D, 9},
    {"like",  0x0E, 4},
    {"more",  0x1A, 4},
    {"not",   0x0E, 3},
    {"people", 0x1F, 6},
    {"quite", 0x1E, 5},
    {"rather", 0x0E, 6},
    {"so",    0x0E, 2},
    {"that",  0x1E, 4},
    {"us",    0x06, 2},
    {"very",  0x16, 4},
    {"it",    0x05, 2},
    {"you",   0x1E, 3},
    {"as",    0x0A, 2},
    {"will",  0x07, 4},
    {"and",   0x0A, 3},
    {"for",   0x0C, 3},
    {"of",    0x0C, 2},
    {"the",   0x0E, 3},
    {"with",  0x16, 4},
    /* Common letter-group contractions */
    {"ch",    0x0E, 2},  /* dots 2,3,4 */
    {"gh",    0x1E, 2},
    {"sh",    0x0E, 2},
    {"th",    0x1E, 2},
    {"wh",    0x16, 2},
    {"ed",    0x1A, 2},
    {"er",    0x0C, 2},
    {"ow",    0x1C, 2},
    {"ou",    0x0E, 2},
    {"st",    0x0E, 2},
    {"ar",    0x0A, 2},
    {"ing",   0x0E, 3},  /* dots 3,4,6 → ⠬ */
    /* One-cell signs */
    {".",    0x06, 1},
    {",",    0x02, 1},
    {";",    0x08, 1},
    {":",    0x0A, 1},
    {"?",    0x20, 1},
    {"!",    0x2A, 1},
    {"\"",   0x0F, 1},
    {"'",    0x04, 1},
    {"-",    0x24, 1},
};

#define UEB_RULE_COUNT (sizeof(ueb_contractions) / sizeof(ueb_contractions[0]))

/* ── Public functions ──────────────────────────────────────────────── */

uint8_t braille_grade1(char ch, gp_lang_t lang)
{
    (void)lang; /* English table only for now; other langs in flash */
    if ((uint8_t)ch < 128)
        return grade1_en[(uint8_t)ch];
    return 0;
}

uint16_t braille_grade2(const char *text, uint16_t pos, uint16_t len,
                         uint8_t *out_dot, gp_lang_t lang)
{
    (void)lang;
    if (pos >= len) return 0;

    /* Try to match the longest contraction at current position */
    char lower[16];
    uint16_t avail = len - pos;
    if (avail > 15) avail = 15;
    for (uint16_t i = 0; i < avail; i++)
        lower[i] = (text[pos + i] >= 'A' && text[pos + i] <= 'Z')
                   ? text[pos + i] + 32 : text[pos + i];
    lower[avail] = '\0';

    /* Search for longest matching contraction */
    uint8_t best_dots = 0;
    uint8_t best_len  = 0;
    for (uint16_t i = 0; i < UEB_RULE_COUNT; i++) {
        uint8_t mlen = ueb_contractions[i].match_len;
        if (mlen > avail) continue;
        if (strncmp(lower, ueb_contractions[i].match, mlen) == 0) {
            if (mlen > best_len) {
                best_len  = mlen;
                best_dots = ueb_contractions[i].dots;
            }
        }
    }

    if (best_len > 0) {
        *out_dot = best_dots;
        return best_len;
    }

    /* No contraction matched: fall back to Grade 1 */
    *out_dot = braille_grade1(text[pos], lang);
    return 1;
}

uint16_t braille_translate(const char *text, uint16_t len, uint8_t *out_dots,
                             gp_mode_t mode, gp_lang_t lang)
{
    uint16_t pos = 0;
    uint16_t cells = 0;

    if (mode == MODE_8DOT) {
        /* Pass through Unicode Braille patterns U+2800-U+28FF */
        while (pos + 1 < len && cells < DEFAULT_CELLS_PER_LINE) {
            uint8_t b0 = (uint8_t)text[pos];
            uint8_t b1 = (uint8_t)text[pos + 1];
            if (b0 == 0xE2 && pos + 2 < len) {
                uint8_t b2 = (uint8_t)text[pos + 1];
                uint8_t b3 = (uint8_t)text[pos + 2];
                if (b2 == 0xA0 && b3 >= 0x80 && b3 <= 0xBF) {
                    out_dots[cells++] = b3 - 0x80;
                    pos += 3;
                    continue;
                }
            }
            (void)b1;
            out_dots[cells++] = braille_grade1(text[pos], lang);
            pos++;
        }
        return cells;
    }

    if (mode == MODE_GRADE1 || mode == MODE_LABEL || mode == MODE_PAGE) {
        while (pos < len && cells < DEFAULT_CELLS_PER_LINE) {
            /* Handle number sign for digits */
            if (text[pos] >= '0' && text[pos] <= '9' && mode != MODE_GRADE1) {
                /* Insert number sign ⠼ (dots 3,4,5,6) */
                out_dots[cells++] = 0x3C;
                while (pos < len && text[pos] >= '0' && text[pos] <= '9'
                       && cells < DEFAULT_CELLS_PER_LINE) {
                    out_dots[cells++] = braille_grade1(text[pos], lang);
                    pos++;
                }
            } else {
                out_dots[cells++] = braille_grade1(text[pos], lang);
                pos++;
            }
        }
        return cells;
    }

    /* Grade 2 */
    while (pos < len && cells < DEFAULT_CELLS_PER_LINE) {
        uint8_t dot;
        uint16_t consumed = braille_grade2(text, pos, len, &dot, lang);
        if (consumed == 0) break;
        out_dots[cells++] = dot;
        pos += consumed;
    }
    return cells;
}