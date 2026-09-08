---
name: first-time-setup
description: First-time setup flow for gzh-image preferences
---

# First-Time Setup

## Overview

Use this flow only when the user explicitly asks to save or reconfigure persistent preferences. A missing `EXTEND.md` does not trigger setup; ordinary generation uses built-in defaults.

Preference setup is separate from ordinary image generation. When requested, batch the questions, save `EXTEND.md`, report its path, and then return to the generation workflow.

## Setup Flow

```
User requests persistent preferences
        │
        ▼
┌─────────────────────┐
│ AskUserQuestion     │
│ (all questions)     │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Create EXTEND.md    │
└─────────────────────┘
        │
        ▼
    Continue to Step 1
```

## Questions

**Language**: Use user's input language or saved language preference.

Prefer the runtime's native user-input tool and batch all questions into one interaction. If unavailable, ask one concise numbered plain-text question containing the same fields.

### Question 1: Watermark

```yaml
header: "Watermark"
question: "Watermark text for generated cover images?"
options:
  - label: "No watermark (Recommended)"
    description: "Clean covers, can enable later in EXTEND.md"
```

### Question 2: Preferred Type

```yaml
header: "Type"
question: "Default cover type preference?"
options:
  - label: "Auto-select (Recommended)"
    description: "Choose based on content analysis each time"
  - label: "hero"
    description: "Large visual impact - product launch, announcements"
  - label: "conceptual"
    description: "Concept visualization - technical, architecture"
```

### Question 3: Preferred Palette

```yaml
header: "Palette"
question: "Default color palette preference?"
options:
  - label: "Auto-select (Recommended)"
    description: "Choose based on content analysis each time"
  - label: "elegant"
    description: "Sophisticated - soft coral, muted teal, dusty rose"
  - label: "warm"
    description: "Friendly - orange, golden yellow, terracotta"
  - label: "cool"
    description: "Technical - engineering blue, navy, cyan"
```

### Question 4: Preferred Rendering

```yaml
header: "Rendering"
question: "Default rendering style preference?"
options:
  - label: "Auto-select (Recommended)"
    description: "Choose based on content analysis each time"
  - label: "hand-drawn"
    description: "Sketchy organic illustration with personal touch"
  - label: "flat-vector"
    description: "Clean modern vector with geometric shapes"
  - label: "digital"
    description: "Polished precise digital illustration"
```

### Question 5: Default Aspect Ratio

```yaml
header: "Aspect"
question: "Default aspect ratio for cover images?"
options:
  - label: "2.35:1 (Recommended)"
    description: "WeChat article header - matches the default public-account cover ratio"
  - label: "16:9"
    description: "Standard widescreen - inline illustrations and versatile use"
  - label: "1:1"
    description: "Square - Instagram, WeChat, social cards"
  - label: "3:4"
    description: "Portrait - Xiaohongshu, Pinterest, mobile content"
```

Note: More ratios (4:3, 3:2) available during generation. This sets the default recommendation.

### Question 6: Default Output Directory

```yaml
header: "Output"
question: "Default output directory for cover images?"
options:
  - label: "Independent (Recommended)"
    description: "cover-image/{topic-slug}/ - separate from article"
  - label: "Same directory"
    description: "{article-dir}/ - alongside the article file"
  - label: "imgs subdirectory"
    description: "{article-dir}/imgs/ - images folder near article"
```

### Question 7: Quick Mode

```yaml
header: "Quick"
question: "Enable quick mode by default?"
options:
  - label: "No (Recommended)"
    description: "Confirm dimension choices each time"
  - label: "Yes"
    description: "Skip confirmation, use auto-selection"
```

### Question 8: Save Location

```yaml
header: "Save"
question: "Where to save preferences?"
options:
  - label: "Project (Recommended)"
    description: ".skillsvc-image/ (this project only)"
  - label: "User"
    description: "~/.skillsvc-image/ (all projects)"
```

## Save Locations

| Choice | Path | Scope |
|--------|------|-------|
| Project | `.skillsvc-image/gzh-image/EXTEND.md` | Current project |
| User | `${XDG_CONFIG_HOME:-$HOME/.config}/skillsvc-image/gzh-image/EXTEND.md` | All projects |
| User fallback | `~/.skillsvc-image/gzh-image/EXTEND.md` | All projects |

## After Setup

1. Create directory if needed
2. Write EXTEND.md with frontmatter
3. Confirm: "Preferences saved to [path]"
4. Continue to Step 1

## EXTEND.md Template

```yaml
---
version: 3
watermark:
  enabled: [true/false]
  content: "[user input or empty]"
  position: bottom-right
  opacity: 0.7
preferred_type: [selected type or null]
preferred_palette: [selected palette or null]
preferred_rendering: [selected rendering or null]
preferred_text: title-only
preferred_mood: balanced
default_aspect: [16:9/2.35:1/1:1/3:4]
default_output_dir: [independent/same-dir/imgs-subdir]
quick_mode: [true/false]
language: null
custom_palettes: []
---
```

## Modifying Preferences Later

See the `## Changing Preferences` section in `SKILL.md` for the canonical list of common edits (change defaults or retrigger setup). Full schema: `preferences-schema.md`.

**EXTEND.md Supports**: Watermark | Preferred type | Preferred palette | Preferred rendering | Preferred text | Preferred mood | Default aspect ratio | Default output directory | Quick mode | Custom palette definitions | Language preference
