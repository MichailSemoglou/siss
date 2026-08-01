# Authoring Siss Constraints Files

A constraints file is a JSON document that describes a complete visual grammar
for the Siss halftone renderer. An LLM writes the JSON; Siss compiles it into
pixels deterministically. Nothing in the pipeline relies on an image-generating
model, so the result is reproducible and auditable.

## Schema

The file is a single JSON object. Every key is optional; missing keys fall
through to Siss defaults. Unknown keys are rejected with an error.

```text
{
  "effect":           string,       "duotone" | "halftone"
  "color1":           color,        foreground / dark-area color
  "color2":           color,        background / light-area color
  "symbol_type":      string,       "plus" | "asterisk" | "slash" | "dot" | "ring"
  "grid_type":        string,       "square" | "hex"
  "symbol_size":      integer,      >=1, pixels for the largest symbol
  "luminance_curve": {
      "gamma":        number,       >0, linear at 1.0
  }
}
```

### Color values

A color is one of:

- A hex string with or without `#`: `"#ff0044"`, `"ff0044"`, `"#f04"`, `"f04"`
- A CSS named color: `"rebeccapurple"`, `"gold"`, `"navy"`
- An RGB triple as a JSON array: `[255, 0, 68]`

`"color1"` is applied to dark regions (halftone symbols, duotone dark end).
`"color2"` is applied to light regions (halftone background, duotone light end).

### Effect

Omit this field or set it to `"halftone"`; the constraints feature targets
the halftone effect. `"duotone"` is supported for completeness but only
`"color1"` and `"color2"` apply.

### Symbol type

| Value      | Shape                                 |
| ---------- | ------------------------------------- |
| `plus`     | Horizontal + vertical cross           |
| `asterisk` | Plus with both diagonals (8-arm star) |
| `slash`    | Single diagonal                       |
| `dot`      | Filled circle                         |
| `ring`     | Hollow circle, one-pixel outline      |

At sizes below 3 pixels the distinction between `dot` and `ring` collapses;
choose `dot` for small-scale work.

### Grid type

| Value    | Behavior                                              |
| -------- | ----------------------------------------------------- |
| `square` | Grid points align in straight columns and rows        |
| `hex`    | Alternating rows offset by half a step, producing the |
|          | interlocking dot screen of traditional print halftone |

`hex` feels organic and analog; `square` feels rigid and digital.

### Symbol size

The size in pixels of the largest symbol. Actual sizes scale linearly from
zero (for white) to `symbol_size` (for black), modulated by the luminance
curve gamma. Typical values range from 6 to 20. Values above 30 produce
chunky, low-resolution grids.

### Luminance curve gamma

```text
gamma = 0.2    extreme shadow amplification, nearly uniform grid
gamma = 0.5    pronounced shadow amplification
gamma = 0.8    mild amplification (example file default)
gamma = 1.0    linear, unchanged from standard Siss
gamma = 1.5    mild shadow suppression
gamma = 2.0    pronounced shadow suppression, high contrast
gamma = 3.0    extreme shadow crushing
```

The gamma exponent is applied to the normalized luminance before the symbol
size is computed: `size = max_size * (1 - luminance/255) ^ gamma`. Values
above 1.0 suppress symbol growth in dark regions (midtones and shadows merge
toward black). Values below 1.0 amplify growth (shadows bloom outward).

## How to author a grammar from a description

The user provides a natural-language description of the visual outcome they
want. You translate it into a JSON constraints file by reasoning about the
parameter semantics below.

### Step 1: Identify the mood and period

The mood drives the color pair. A warm, nostalgic palette uses earthy tones;
a cold, clinical one uses blue-white/cyan. The period drives the grid and
symbol: a 1970s newspaper feel wants `hex` grid with `dot` symbols; a
punk-rock poster wants `slash` symbols on a `square` grid.

### Step 2: Choose colors

Prefer named CSS colors or hex triples. For a vintage print look, start from
cream, sepia, newsprint-gray, or deep indigo. For a synthetic look, start
from neon green, electric blue, hot pink. Avoid true black `#000000` or
white `#ffffff` as a pairing unless the user asks for it; off-white and
off-black read better in rendered output.

### Step 3: Decide gamma

| Desired outcome                         | Gamma range |
| --------------------------------------- | ----------- |
| Soft, washed-out, dreamy                | 0.5 – 0.7   |
| Mild shadow bloom, slight amplification | 0.8 – 0.9   |
| Linear, neutral, no bias                | 1.0         |
| High contrast, stark, graphic           | 1.5 – 2.0   |
| Crushed shadows, silhouette             | 2.0 – 3.0   |

### Step 4: Pick grid and symbol

| Look                        | Grid   | Symbol   |
| --------------------------- | ------ | -------- |
| Traditional print halftone  | hex    | dot      |
| Newspaper rotogravure       | hex    | ring     |
| Vector plotter, blueprint   | square | plus     |
| Punk, zine, DIY             | square | slash    |
| Glitch, digital, aggressive | square | asterisk |

### Step 5: Size for the medium

| Use case               | symbol_size |
| ---------------------- | ----------- |
| Social-media thumbnail | 4 – 8       |
| Standard web image     | 8 – 14      |
| Print at magazine size | 10 – 20     |
| Large-format poster    | 15 – 30     |

## Examples

### High-contrast zine cover

**User:** “A black-and-white halftone like a photocopied punk fanzine cover.”

```json
{
  "effect": "halftone",
  "color1": "#111111",
  "color2": "#fafafa",
  "symbol_type": "slash",
  "grid_type": "square",
  "symbol_size": 14,
  "luminance_curve": { "gamma": 2.0 }
}
```

Explanation: off-black on off-white avoids harsh clipping, `slash` is
aggressive, `square` grid is rigid, gamma 2.0 crushes midtones into shadow.

### 1970s newspaper

**User:** “A warm halftone that looks like a 1970s newspaper photograph.”

```json
{
  "effect": "halftone",
  "color1": "#2b1b0e",
  "color2": "#f5e6c8",
  "symbol_type": "dot",
  "grid_type": "hex",
  "symbol_size": 10,
  "luminance_curve": { "gamma": 0.8 }
}
```

Explanation: dark brown ink on cream paper, classic `dot` on `hex` grid,
mild gamma amplification for the soft shadow bloom of newsprint.

### Neon cyberpunk

**User:** “Electric blue symbols on a dark purple background, like a synthwave
album cover.”

```json
{
  "effect": "halftone",
  "color1": "#00e5ff",
  "color2": "#1a0030",
  "symbol_type": "asterisk",
  "grid_type": "hex",
  "symbol_size": 12,
  "luminance_curve": { "gamma": 1.0 }
}
```

Explanation: cyan-on-deep-purple, `asterisk` for the glitchy star-burst feel,
neutral gamma to keep midtones visible.

### Dream-poppy wash

**User:** “Something soft and dreamy, barely there, like faded memory.”

```json
{
  "effect": "halftone",
  "color1": "#c9a0dc",
  "color2": "#fdf6e3",
  "symbol_type": "ring",
  "grid_type": "hex",
  "symbol_size": 8,
  "luminance_curve": { "gamma": 0.5 }
}
```

Explanation: low-contrast lavender on cream fades into the background,
`ring` symbols leave open centers for an airy feel, `hex` for organic
flow, gamma 0.5 amplifies the soft shadows.

## Rules for the LLM

1. Output only the JSON constraints object. No preamble, no explanation, no
   markdown fences unless the user asks for prose.
2. Every field is optional. Omit fields where the Siss default is acceptable
   rather than repeating defaults.
3. Never invent new keys. The fixed key set is closed; unknown keys are
   rejected at render time.
4. `color1` and `color2` must be valid hex strings, CSS names, or `[r, g, b]`
   arrays. Invalid color strings cause a hard error at render time.
5. `luminance_curve.gamma` must be strictly greater than 0. Negative gamma
   and zero are rejected.
6. `symbol_type` and `grid_type` must match the enumerated values exactly.
7. `symbol_size` must be a positive integer.
8. Match gamma, grid, and symbol type to the described mood and period. Do
   not default to `dot`/`hex`/`1.0` unless the description is neutral.
9. If the user provides no visual cues at all, ask one clarifying question
   about the desired mood or period before generating a file.
10. Do not attempt to describe what the output will look like in the JSON.
    The constraints file is a machine-readable spec, not a critique.
