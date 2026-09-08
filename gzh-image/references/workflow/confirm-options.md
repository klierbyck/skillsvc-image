# Step 2: Confirm Options

## Purpose

Resolve only the choices that are both unspecified and material to the result.

本文件中的 `--quick`、`--type`、`--style`、`--palette`、`--rendering`、`--font` 和 `--aspect` 是技能规划选项的简写，不是 `scripts/generate_image.py` 参数。确认后应把这些选择展开到 prompt，或映射成 CLI 支持的 `--aspect-ratio` 等参数。

## Skip Conditions

| Condition | Behavior |
|-----------|----------|
| `--quick`, equivalent wording, or `quick_mode: true` | Ask nothing; use explicit values, then preferences, then built-in defaults |
| All required choices specified | Ask nothing |
| Only non-critical choices missing | Use defaults without blocking |
| A material ambiguity remains | Ask only the ambiguous choices in one interaction |

The public-account cover default is `2.35:1`; inline illustrations default to `16:9`. Do not ask for an aspect ratio merely because `--aspect` was omitted.

## Quick Mode Output

When confirmation is skipped, report the resolved values and proceed:

```
Quick Mode: Auto-selected dimensions
• Type: [type] ([reason])
• Palette: [palette] ([reason])
• Rendering: [rendering] ([reason])
• Text: [text] ([reason])
• Mood: [mood] ([reason])
• Font: [font] ([reason])

• Aspect Ratio: [ratio] ([explicit request / saved preference / platform default])
```

## Confirmation Flow

**Language**: Auto-determined (user's input language > saved preference > source language). No need to ask.

Prefer the runtime's built-in user-input tool and batch unresolved choices into one interaction. If no such tool exists, ask one concise numbered plain-text question.

Skip any question where the dimension is already specified in the current request or by a selected style preset.

### Q1: Type (skip if `--type`)

```yaml
header: "Type"
question: "Which cover type?"
multiSelect: false
options:
  - label: "[auto-recommended type] (Recommended)"
    description: "[reason based on content signals]"
  - label: "hero"
    description: "Large visual impact, title overlay - product launch, announcements"
  - label: "conceptual"
    description: "Concept visualization - technical, architecture"
  - label: "typography"
    description: "Text-focused layout - opinions, quotes"
```

### Q2: Palette (skip if `--palette` or `--style`)

```yaml
header: "Palette"
question: "Which color palette?"
multiSelect: false
options:
  - label: "[auto-recommended palette] (Recommended)"
    description: "[reason based on content signals]"
  - label: "warm"
    description: "Friendly - orange, golden yellow, terracotta"
  - label: "elegant"
    description: "Sophisticated - soft coral, muted teal, dusty rose"
  - label: "cool"
    description: "Technical - engineering blue, navy, cyan"
```

### Q3: Rendering (skip if `--rendering` or `--style`)

Show compatible renderings (✓✓ first from compatibility matrix):

```yaml
header: "Rendering"
question: "Which rendering style?"
multiSelect: false
options:
  - label: "[best compatible rendering] (Recommended)"
    description: "[reason based on palette + type + content]"
  - label: "flat-vector"
    description: "Clean outlines, flat fills, geometric icons"
  - label: "hand-drawn"
    description: "Sketchy, organic, imperfect strokes"
  - label: "digital"
    description: "Polished, precise, subtle gradients"
```

### Q4: Font (skip if `--font`)

```yaml
header: "Font"
question: "Which font style?"
multiSelect: false
options:
  - label: "[auto-recommended font] (Recommended)"
    description: "[reason based on content signals]"
  - label: "clean"
    description: "Modern geometric sans-serif - tech, professional"
  - label: "handwritten"
    description: "Warm hand-lettered - personal, friendly"
  - label: "serif"
    description: "Classic elegant - editorial, luxury"
  - label: "display"
    description: "Bold decorative - announcements, entertainment"
```

### Q5: Other Settings (skip if all remaining dimensions already specified)

Combine remaining settings into one question. Include: Output Dir (if no preference + file path input), Text, Mood, Aspect. Show auto-selected values as recommended option. User can accept all or type adjustments via "Other".

**When output dir needs asking** (no `default_output_dir` preference + file path input):

```yaml
header: "Settings"
question: "Output / Text / Mood / Aspect?"
multiSelect: false
options:
  - label: "imgs/ / [auto-text] / [auto-mood] / [preset-aspect] (Recommended)"
    description: "{article-dir}/imgs/, [text reason], [mood reason], [aspect source]"
  - label: "same-dir / [auto-text] / [auto-mood] / [preset-aspect]"
    description: "{article-dir}/, same directory as article"
  - label: "independent / [auto-text] / [auto-mood] / [preset-aspect]"
    description: "cover-image/{topic-slug}/, separate from article"
```

**When output dir already set** (preference exists or pasted content):

```yaml
header: "Settings"
question: "Text / Mood / Aspect?"
multiSelect: false
options:
  - label: "[auto-text] / [auto-mood] / [preset-aspect] (Recommended)"
    description: "Auto-selected: [text reason], [mood reason], [aspect source]"
  - label: "[auto-text] / bold / [preset-aspect]"
    description: "High contrast, vivid — matches [content signal]"
  - label: "[auto-text] / subtle / [preset-aspect]"
    description: "Low contrast, muted — calm, professional"
```

*Note*: "Other" (auto-added) allows typing custom combo. Parse `/`-separated values matching the question format.

## After Response

Proceed to Step 3 with the resolved dimensions. Confirmation may come from the user, explicit request parameters, saved preferences, or built-in defaults under the rules above.
