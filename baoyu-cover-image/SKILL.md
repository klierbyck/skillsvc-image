---
name: baoyu-cover-image
description: 为微信公众号文章生成封面和正文配图；作为扩展，也可在用户要求“写公众号文章并配图”时整理正文后完成整套图片。仅把公众号内容作为参考、明确只要文字不要图片，或目标是小红书/贴图号时不要使用。
metadata:
  openclaw:
    homepage: https://github.com/JimLiu/baoyu-skills#baoyu-cover-image
---

# WeChat Cover and Article Illustration Generator

Generate context-aware WeChat covers and inline illustrations, with optional article writing only when needed for a complete illustrated deliverable.

## Platform Routing

- 公众号封面、公众号正文配图、公众号图文，或“写公众号文章并配图”时使用本技能。
- 若同一请求还出现贴图、贴图号、微信贴图、公众号贴图、小红书、小绿书、XHS 或 RedNote，则不要使用本技能，改由 `baoyu-xhs-images` 处理图片卡片。
- 微信公众号头条封面默认 `2.35:1`、`2K`；公众号正文配图默认 `16:9`、`2K`。用户明确指定的宽高比和图片尺寸优先。
- “参考公众号文章”只说明参考材料来源；如果用户要求的最终产物不是公众号文章，则不要因此触发本技能。
- 本技能只负责文章、封面和正文插图的本地生成，不登录、上传或发布到微信公众号。
- 图片生成是本技能的主任务；文章写作只在最终交付物包含图片时作为扩展，用来提供完整上下文和图片位置。本目录属于 `skillsvc-image` 技能包，图片请求统一由技能包根目录的 CLI 执行。

## Task Modes

- **Cover only**: 用户只要求封面或头图时，使用原有封面工作流，不额外写文章或生成正文插图。
- **Existing article illustration**: 用户已有正文时，不重写正文，除非用户明确要求；根据全文结构补充封面和正文插图。
- **Direct illustrated article**: 用户要求写公众号文章并配图且只提供主题时，整理完整正文，再规划封面和正文配图。
- **Reference-based illustrated article**: 用户要求图文成品并提供参考时，借鉴结构、语气、信息组织和视觉节奏，创作新的正文及配图。

## Content Reference Policy

References are optional and advisory by default. Do not require a reference before writing. Do not copy wording or treat every reference detail as mandatory. Only constraints explicitly marked by the user as required, exact, unchanged, or strict become hard requirements. The requested output format always takes priority over the source platform of a reference.

## User Input Tools

When this skill prompts the user, follow this tool-selection rule (priority order):

1. **Prefer built-in user-input tools** exposed by the current agent runtime — e.g., `AskUserQuestion`, `request_user_input`, `clarify`, `ask_user`, or any equivalent.
2. **Fallback**: if no such tool exists, emit a numbered plain-text message and ask the user to reply with the chosen number/answer for each question.
3. **Batching**: if the tool supports multiple questions per call, combine all applicable questions into a single call; if only single-question, ask them one at a time in priority order.

Concrete `AskUserQuestion` references below are examples — substitute the local equivalent in other runtimes.

## Image Generation Backend

始终使用当前 `skillsvc-image` 技能包根目录的生图 CLI，不选择或询问其他生图后端。默认使用 `gpt-image-2`；只有用户明确指定 Banana、Nano Banana、nanobanana、香蕉生图或 `nana-banana-2` 时才切换模型。

The stable CLI contract is:

```bash
python3 <skillsvc-image>/scripts/generate_image.py generate --prompt "..." --context-file <prompt-file> --aspect-ratio <ratio> --image-size 2K
python3 <skillsvc-image>/scripts/generate_image.py reference --image <ref> --prompt "..." --context-file <prompt-file> --aspect-ratio <ratio> --image-size 2K
python3 <skillsvc-image>/scripts/generate_image.py edit --session <session.json> --prompt "..."
```

先解析当前 `SKILL.md` 的真实路径；其父目录即技能包根目录 `<skillsvc-image>`，CLI 位于 `<skillsvc-image>/scripts/generate_image.py`。保留封面返回的 session JSON，后续修改应编辑已有图片而不是重新开始。

**⛔ Never substitute SVG, HTML, canvas, or other code-based rendering for raster image generation.** If `$skillsvc-image` is unavailable or its API fails, report the problem instead of silently changing the output medium.

**⛔ Never repair rendered text by painting over a generated bitmap.** Do not use ImageMagick, Pillow, Canvas, SVG, HTML/CSS, OCR scripts, or any other programmatic overlay to cover, rewrite, erase, stroke, or replace title/subtitle text inside an already generated cover image. If text is wrong or unclear, regenerate from a corrected prompt, switch to a lower-text or no-title variant, or ask the user which imperfect candidate to keep.

**Prompt file requirement (hard)**: write each image's full, final prompt to a standalone file under `prompts/` (naming: `NN-{type}-[slug].md`) BEFORE invoking `$skillsvc-image`. The file is the reproducibility record for later regeneration and editing.

## Confirmation Policy

Default behavior: **confirm before generation**.

- Treat explicit skill invocation, a file path, matched keywords/presets, `EXTEND.md` defaults, and any documented auto-selection as **recommendation inputs only**. None of them authorizes skipping confirmation.
- Do **not** start Step 3 or Step 4 until the user confirms the dimensions / aspect / language choices.
- Skip confirmation only when the current request explicitly says to do so, for example: `--quick`, "直接生成", "不用确认", "跳过确认", "按默认出图", or equivalent wording. `quick_mode: true` in `EXTEND.md` counts as a standing explicit opt-out — set it only when you want every run to skip Step 2.
- If confirmation is skipped explicitly, state the assumed dimensions / aspect / language / model in the next user-facing update before generating.

## Options

| Option | Description |
|--------|-------------|
| `--type <name>` | hero, conceptual, typography, metaphor, scene, minimal |
| `--palette <name>` | warm, elegant, cool, dark, earth, vivid, pastel, mono, retro, duotone, macaron |
| `--rendering <name>` | flat-vector, hand-drawn, painterly, digital, pixel, chalk, screen-print |
| `--style <name>` | Preset shorthand (see [Style Presets](references/style-presets.md)) |
| `--text <level>` | none, title-only, title-subtitle, text-rich |
| `--mood <level>` | subtle, balanced, bold |
| `--font <name>` | clean, handwritten, serif, display |
| `--aspect <ratio>` | 2.35:1 (公众号封面默认), 16:9, 4:3, 3:2, 1:1, 3:4 |
| `--lang <code>` | Title language (en, zh, ja, etc.) |
| `--no-title` | Alias for `--text none` |
| `--quick` | Skip confirmation, use auto-selection |
| `--ref <files...>` | Reference images for style/composition guidance |

## Five Dimensions

| Dimension | Values | Default |
|-----------|--------|---------|
| **Type** | hero, conceptual, typography, metaphor, scene, minimal | auto |
| **Palette** | warm, elegant, cool, dark, earth, vivid, pastel, mono, retro, duotone, macaron | auto |
| **Rendering** | flat-vector, hand-drawn, painterly, digital, pixel, chalk, screen-print | auto |
| **Text** | none, title-only, title-subtitle, text-rich | title-only |
| **Mood** | subtle, balanced, bold | balanced |
| **Font** | clean, handwritten, serif, display | clean |

Auto-selection rules: [references/auto-selection.md](references/auto-selection.md)

## Galleries

**Types**: hero, conceptual, typography, metaphor, scene, minimal
→ Details: [references/types.md](references/types.md)

**Palettes**: warm, elegant, cool, dark, earth, vivid, pastel, mono, retro, duotone, macaron
→ Details: [references/palettes/](references/palettes/)

**Renderings**: flat-vector, hand-drawn, painterly, digital, pixel, chalk, screen-print
→ Details: [references/renderings/](references/renderings/)

**Text Levels**: none (pure visual) | title-only (default) | title-subtitle | text-rich (with tags)
→ Details: [references/dimensions/text.md](references/dimensions/text.md)

**Mood Levels**: subtle (low contrast) | balanced (default) | bold (high contrast)
→ Details: [references/dimensions/mood.md](references/dimensions/mood.md)

**Fonts**: clean (sans-serif) | handwritten | serif | display (bold decorative)
→ Details: [references/dimensions/font.md](references/dimensions/font.md)

## File Structure

Output directory per `default_output_dir` preference:
- `same-dir`: `{article-dir}/`
- `imgs-subdir`: `{article-dir}/imgs/`
- `independent` (default): `cover-image/{topic-slug}/`

```
<output-dir>/
├── source-{slug}.{ext}    # Source files
├── refs/                  # Reference images (if provided)
│   ├── ref-01-{slug}.{ext}
│   └── ref-01-{slug}.md   # Description file
├── prompts/cover.md       # Generation prompt
└── cover.png              # Output image
```

**Slug**: 2-4 words, kebab-case. Conflict: append `-YYYYMMDD-HHMMSS`

For full article tasks, use this extended layout:

```text
wechat-article/{topic-slug}/
├── source-references/          # optional reference material
├── article.md                  # completed original article
├── visual-plan.md              # cover and inline image positions
├── prompts/
│   ├── cover.md
│   └── illustration-NN.md
├── cover.png
├── illustration-NN.png
└── session-*.json              # one editing session per image
```

## Illustrated Article Extension

Use this extension only when the requested deliverable includes images. It supports direct illustrated articles, reference-based illustrated articles, and existing articles that need multiple images:

1. After loading preferences, determine the intended audience, purpose, tone, approximate length, and whether the user wants a new article or edits to an existing draft. Infer reasonable defaults when these details are not specified.
2. If references exist, save or record them under `source-references/` and extract reusable ideas. Treat them as optional inspiration, not as an outline that must be copied.
3. Write and save the complete article to `article.md`. Do not invent personal experience, test results, quotes, or factual claims that are not supported by the user's material.
4. Read the completed article as a whole and create `visual-plan.md`. Include one cover plus only the inline images that materially explain, compare, demonstrate, establish atmosphere, or improve reading rhythm. Record each image's purpose and exact insertion point.
5. Generate the cover with the existing five-dimension cover rules at `2.35:1`, `2K` unless the user specifies otherwise.
6. Generate every inline illustration from its surrounding paragraphs plus the article's shared visual direction at `16:9`, `2K` unless overridden. Use a separate `$skillsvc-image` session for each image.
7. Insert relative image paths and concise captions into a new or generated `article.md`. When the user supplied an existing file, preserve it and write a new illustrated copy unless modification was explicitly authorized.
8. Return the article, visual plan, images, prompts, and session paths. Stop without publishing.

## Workflow

### Progress Checklist

```
Cover Image Progress:
- [ ] Step 0: Check preferences (EXTEND.md) ⛔ BLOCKING
- [ ] Step 1: Analyze content + save refs + determine output dir
- [ ] Step 2: Confirm options (6 dimensions) ⚠️ unless --quick
- [ ] Step 3: Create prompt
- [ ] Step 4: Generate image
- [ ] Step 5: Completion report
```

### Flow

```
Input → [Step 0: Preferences] ─┬─ Found → Continue
                               └─ Not found → First-Time Setup ⛔ BLOCKING → Save EXTEND.md → Continue
        ↓
Analyze + Save Refs → [Output Dir] → [Confirm: 6 Dimensions] → Prompt → Generate → Complete
                                              ↓
                                     (skip if --quick or all specified)
```

### Step 0: Load Preferences ⛔ BLOCKING

Check EXTEND.md in priority order — the first one found wins:

| Priority | Path | Scope |
|----------|------|-------|
| 1 | `.baoyu-skills/baoyu-cover-image/EXTEND.md` | Project |
| 2 | `${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/baoyu-cover-image/EXTEND.md` | XDG |
| 3 | `$HOME/.baoyu-skills/baoyu-cover-image/EXTEND.md` | User home |

| Result | Action |
|--------|--------|
| Found | Load, display summary → Continue |
| Not found | ⛔ Run first-time setup ([references/config/first-time-setup.md](references/config/first-time-setup.md)) → Save → Continue |

**CRITICAL**: If not found, complete setup BEFORE any other steps or questions.

### Step 1: Analyze Content

1. **Save reference images** (if provided) → [references/workflow/reference-images.md](references/workflow/reference-images.md)
2. **Save source content** (if pasted, save to `source.md`)
3. **Analyze content**: topic, tone, keywords, visual metaphors
4. **Deep analyze references** ⚠️: Extract specific, concrete elements (see reference-images.md)
5. **Detect language**: Compare source, user input, EXTEND.md preference
6. **Determine output directory**: Per File Structure rules

**⚠️ People in Reference Images:**

If reference images contain **people** who should appear in the cover, copy each image to `refs/`, then pass it through `$skillsvc-image reference --image`. Also describe each character's hair, glasses, skin tone, clothing, and required transformation in the prompt so the reference is applied deliberately.

See [reference-images.md](references/workflow/reference-images.md) for full decision table.

### Step 2: Confirm Options ⚠️

**Hard gate**: this step is mandatory per the [Confirmation Policy](#confirmation-policy) — Steps 3–4 cannot start until the user confirms here (or explicitly opts out with `--quick` / `quick_mode: true` / equivalent wording in the current request).

**MUST use `AskUserQuestion` tool** to present options as interactive selection — NOT plain text tables. Present up to 4 questions in a single `AskUserQuestion` call (Type, Palette, Rendering, Font + Settings). Each question shows the recommended option first with reason, followed by alternatives.

Full confirmation flow and question format: [references/workflow/confirm-options.md](references/workflow/confirm-options.md)

| Condition | Skipped | Still Asked |
|-----------|---------|-------------|
| `--quick` or `quick_mode: true` | 6 dimensions | Aspect ratio (unless `--aspect`) |
| All 6 + `--aspect` specified | All | None |

### Step 3: Create Prompt

Save to `prompts/cover.md`. Template: [references/workflow/prompt-template.md](references/workflow/prompt-template.md)

**CRITICAL - References in Frontmatter**:
- Files saved to `refs/` → Add to frontmatter `references` list
- Style extracted verbally (no file) → Omit `references`, describe in body
- Before writing → Verify: `test -f refs/ref-NN-{slug}.{ext}`

**Reference elements in body** MUST be detailed, prefixed with "MUST"/"REQUIRED", with integration approach.

### Step 4: Generate Image

1. **Backup existing** `cover.png` if regenerating
2. **Write the full final prompt** to `prompts/01-cover-[slug].md` (hard requirement) BEFORE invoking the backend.
3. **Process references** from prompt frontmatter:
   - `direct` usage → use `$skillsvc-image reference` and pass every file with a separate `--image`
   - `style`/`palette` → extract traits, append to prompt
4. **Generate** with `$skillsvc-image`, passing the saved prompt file as `--context-file`, the planned output path, `--image-size 2K`, and the resolved aspect ratio.
   - No reference image → `generate`
   - One or more reference images → `reference`
   - Later revisions of this cover → `edit --session <returned-session.json>`
5. On failure: auto-retry once

### Step 5: Completion Report

```
Cover Generated!

Topic: [topic]
Type: [type] | Palette: [palette] | Rendering: [rendering]
Text: [text] | Mood: [mood] | Font: [font] | Aspect: [ratio]
Title: [title or "visual only"]
Language: [lang] | Watermark: [enabled/disabled]
References: [N images or "extracted style" or "none"]
Location: [directory path]

Files:
✓ source-{slug}.{ext}
✓ prompts/cover.md
✓ cover.png
```

## Image Modification

| Action | Steps |
|--------|-------|
| **Regenerate** | Backup → Update prompt file FIRST → Regenerate |
| **Change dimension** | Backup → Confirm new value → Update prompt → Regenerate |

Text correction policy:

- If the title/subtitle is misspelled, garbled, hard to read, or visually weak, do not patch the bitmap with code.
- For text-correction regenerations, write a new prompt file and a new output path so the flawed candidate is preserved for comparison.
- Post-processing is limited to crop, resize, compression, or format conversion that does not alter text or the main composition.

## Composition Principles

- **Whitespace**: 40-60% breathing room
- **Visual anchor**: Main element centered or offset left
- **Characters**: Simplified silhouettes; NO realistic humans
- **Title**: Use exact title from user/source; never invent

## Changing Preferences

EXTEND.md lives at the path noted in **Step 0**. Three ways to change it:

- **Edit directly** — open EXTEND.md and change fields. Full schema: [references/config/preferences-schema.md](references/config/preferences-schema.md).
- **Reconfigure interactively** — delete EXTEND.md (or ask "reconfigure baoyu-cover-image preferences" / "重新配置"). The next run re-triggers first-time setup.
- **Common one-line edits**:
  - `watermark.enabled: true`, `preferred_type`, `preferred_palette`, `preferred_rendering`, `default_aspect`, `quick_mode: true`, `language` — shift the auto-selection defaults and confirmation flow.

## References

**Dimensions**: [text.md](references/dimensions/text.md) | [mood.md](references/dimensions/mood.md) | [font.md](references/dimensions/font.md)
**Palettes**: [references/palettes/](references/palettes/)
**Renderings**: [references/renderings/](references/renderings/)
**Types**: [references/types.md](references/types.md)
**Auto-Selection**: [references/auto-selection.md](references/auto-selection.md)
**Style Presets**: [references/style-presets.md](references/style-presets.md)
**Compatibility**: [references/compatibility.md](references/compatibility.md)
**Visual Elements**: [references/visual-elements.md](references/visual-elements.md)
**Workflow**: [confirm-options.md](references/workflow/confirm-options.md) | [prompt-template.md](references/workflow/prompt-template.md) | [reference-images.md](references/workflow/reference-images.md)
**Config**: [preferences-schema.md](references/config/preferences-schema.md) | [first-time-setup.md](references/config/first-time-setup.md) | [watermark-guide.md](references/config/watermark-guide.md)
