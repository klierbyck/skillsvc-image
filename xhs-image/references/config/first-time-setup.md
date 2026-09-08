---
name: first-time-setup
description: First-time setup flow for xhs-image preferences
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

```
header: "Watermark"
question: "Watermark text for generated images? Type your watermark content (e.g., name, @handle)"
options:
  - label: "No watermark (Recommended)"
    description: "No watermark, can enable later in EXTEND.md"
```

Position defaults to bottom-right.

### Question 2: Preferred Style

```
header: "Style"
question: "Default visual style preference? Or type another style name or your custom style"
options:
  - label: "None (Recommended)"
    description: "Auto-select based on content analysis"
  - label: "cute"
    description: "Sweet, adorable - classic XHS aesthetic"
  - label: "notion"
    description: "Minimalist hand-drawn, intellectual"
```

### Question 3: Save Location

```
header: "Save"
question: "Where to save preferences?"
options:
  - label: "Project"
    description: ".skillsvc-image/ (this project only)"
  - label: "User"
    description: "~/.skillsvc-image/ (all projects)"
```

## Save Locations

| Choice | Path | Scope |
|--------|------|-------|
| Project | `.skillsvc-image/xhs-image/EXTEND.md` | Current project |
| User | `${XDG_CONFIG_HOME:-$HOME/.config}/skillsvc-image/xhs-image/EXTEND.md` | All projects |
| User fallback | `~/.skillsvc-image/xhs-image/EXTEND.md` | All projects |

## After Setup

1. Create directory if needed
2. Write EXTEND.md with frontmatter
3. Confirm: "Preferences saved to [path]"
4. Continue to Step 1

## EXTEND.md Template

```yaml
---
version: 1
watermark:
  enabled: [true/false]
  content: "[user input or empty]"
  position: bottom-right
  opacity: 0.7
preferred_style:
  name: [selected style or null]
  description: ""
preferred_layout: null
language: null
generation_batch_size: 4
custom_styles: []
---
```

`generation_batch_size: 4` is the baked-in default for batch rendering. The current user request may override it for one run.

## Modifying Preferences Later

See the `## Changing Preferences` section in `SKILL.md` for the canonical list of common edits (change defaults or retrigger setup). Full schema: `preferences-schema.md`.
