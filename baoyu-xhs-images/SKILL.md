---
name: baoyu-xhs-images
description: 为小红书、小绿书、XHS、RedNote、贴图或贴图号生成 1-10 张连续图片卡片；作为扩展，可从主题或参考内容整理配套平台文案。写小红书或贴图号默认按图文任务处理；用户明确只要文字不要图片，或普通公众号文章/封面且未提到贴图时不要使用。
metadata:
  openclaw:
    homepage: https://github.com/JimLiu/baoyu-skills#baoyu-xhs-images
---

# Xiaohongshu and Tietu Image Card Generator

Generate eye-catching image card series, preparing only the platform copy needed for a complete illustrated deliverable.

## Platform Routing

- 写小红书、XHS、RedNote、小绿书、贴图、贴图号、微信贴图或公众号贴图内容时使用本技能，即使用户没有单独说“生成图片”。
- 只有用户明确说明“只要文字”或“不要图片”时，才把这类请求视为技能范围外的纯文字任务。
- 只提到公众号、公众号文章或公众号封面，且没有贴图类关键词时，不要使用本技能，改由 `baoyu-cover-image` 处理。
- 每张卡片默认 `3:4`、`2K`；用户明确指定的宽高比和图片尺寸优先。
- “参考某篇公众号文章/小红书”只表示参考来源，最终仍按用户要求的小红书或贴图号格式创作。
- 本技能只生成文案和图片文件，不登录、上传或发布到任何平台。
- 图片卡片生成是本技能的主任务；平台文案只在最终交付物包含图片时作为图文扩展，为卡片拆分和上下文提供依据。本目录属于 `skillsvc-image` 技能包，图片请求统一由技能包根目录的 CLI 执行。

## Task Modes

- **Cards only**: 用户明确只要图片卡片时，可以跳过独立文案交付，但仍要先整理出卡片所需的内容结构。
- **Existing copy to cards**: 用户已经给出最终文案时，默认直接据此规划卡片；只有用户要求时才改写正文。
- **Direct illustrated post**: 用户要求小红书或贴图号图文且只给主题时，整理必要的平台文案，再拆分图片卡片。
- **Reference-based illustrated post**: 用户要求图文并提供参考时，借鉴选题角度、结构、语气、信息组织或视觉节奏，重新整理文案和卡片。

## Content Reference Policy

References are optional and advisory by default. Never block direct writing because no reference was supplied. Do not copy source wording, force the same structure, or treat the source platform as the target platform. Only user-marked exact text, facts, people, products, brand elements, or visual traits are hard constraints.

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
python3 <skillsvc-image>/scripts/generate_image.py generate --prompt "..." --context-file <prompt-file> --aspect-ratio 3:4 --image-size 2K
python3 <skillsvc-image>/scripts/generate_image.py reference --image <image-01> --prompt "..." --context-file <prompt-file> --aspect-ratio 3:4 --image-size 2K
python3 <skillsvc-image>/scripts/generate_image.py edit --session <card-session.json> --prompt "..."
```

先解析当前 `SKILL.md` 的真实路径；其父目录即技能包根目录 `<skillsvc-image>`，CLI 位于 `<skillsvc-image>/scripts/generate_image.py`。每张卡片保留一个返回的 session JSON，以便分别修改。

**⛔ Never substitute SVG, HTML, canvas, or other code-based rendering for raster image generation.** If `$skillsvc-image` is unavailable or its API fails, report the problem instead of silently changing the output medium.

**⛔ Never repair rendered text by painting over a generated bitmap.** Do not use ImageMagick, Pillow, Canvas, SVG, HTML/CSS, OCR scripts, or any other programmatic overlay to cover, rewrite, erase, stroke, or replace titles, body copy, tags, or any other text inside an already generated image card. If text is wrong or unclear, regenerate from a corrected prompt, switch to a layout with less on-card text, or ask the user which imperfect candidate to keep.

**Prompt file requirement (hard)**: write each image's full, final prompt to a standalone file under `prompts/` (naming: `NN-{type}-[slug].md`) BEFORE invoking `$skillsvc-image`. The file is the reproducibility record for later regeneration and editing.

## Batch Generation Policy

After every prompt file for the current generation group has been saved and verified, generate images in batches by default.

After image 1 establishes the visual anchor, use runtime parallel tool calls to dispatch up to `generation_batch_size` independent `$skillsvc-image reference` commands at a time. Default: `4`. An explicit user request in the current message, such as `--batch-size 4` or "并行 4 张一起生成", overrides EXTEND.md. If parallel tool calls are unavailable, generate sequentially.

Rules:

- Honor the image-1 anchor chain: generate image 1 first, then batch images 2+ using image 1 as the reference.
- Never start a batch until every selected prompt file for that batch exists on disk.
- Retry failed items once without regenerating successful items.
- Do not use subagents merely to parallelize image rendering. Use subagents only for separate prompt iteration or creative exploration.

## Confirmation Policy

Default behavior: **confirm before generation**.

- Treat explicit skill invocation, a file path, matched signals/presets, and `EXTEND.md` defaults as **recommendation inputs only**. None of them authorizes skipping confirmation.
- Do **not** start Step 3 until the user completes Step 2.
- Skip confirmation only when the current request explicitly says to do so, for example: `--yes`, "直接生成", "不用确认", "跳过确认", "按默认出图", or equivalent wording.
- If confirmation is skipped explicitly, state the assumed strategy / style / layout / palette / count / model in the next user-facing update before generating.

## Language

Respond in the user's language across questions, progress, errors, and completion summary. Keep technical tokens (style names, file paths, code) in English.

## Options

| Option | Description |
|--------|-------------|
| `--style <name>` | Visual style (see Styles below) |
| `--layout <name>` | Information layout (see Layouts below) |
| `--palette <name>` | Color override: macaron / warm / neon |
| `--preset <name>` | Style + layout + optional palette shorthand (see Presets below; per-preset prompt fragments in `references/style-presets.md`) |
| `--ref <files...>` | Reference images applied to image 1 as the series anchor |
| `--batch-size <n>` | Temporary generation batch size for this run. Default: `generation_batch_size` from EXTEND.md, otherwise 4. Clamp to 1-8. |
| `--yes` | Non-interactive: skip all confirmations, use EXTEND.md or built-in defaults, auto-confirm recommended plan (Path A) |

## Dimensions

Three independent knobs combine freely:

| Dimension | Controls | Options |
|-----------|----------|---------|
| **Style** | Visual aesthetics (lines, decorations, rendering) | 12 styles (see Styles below) |
| **Layout** | Information structure (density, arrangement) | 8 layouts (see Layouts below) |
| **Palette** (optional) | Color override, replaces the style's default colors | macaron / warm / neon (see Palettes below) |

Example: `--style notion --layout dense` makes an intellectual knowledge card; add `--palette macaron` to soften the colors without changing notion's rendering rules. A `--preset` is a shorthand for style + layout (+ optional palette).

**Palette behavior**: no `--palette` → style's built-in colors; `--palette <name>` → overrides colors only, rendering rules unchanged. Some styles declare a `default_palette` (e.g., sketch-notes defaults to macaron).

## Styles (12)

| Style | Description |
|-------|-------------|
| `cute` (Default) | Sweet, adorable, girly aesthetic |
| `fresh` | Clean, refreshing, natural |
| `warm` | Cozy, friendly, approachable |
| `bold` | High impact, attention-grabbing |
| `minimal` | Ultra-clean, sophisticated |
| `retro` | Vintage, nostalgic, trendy |
| `pop` | Vibrant, energetic, eye-catching |
| `notion` | Minimalist hand-drawn line art, intellectual |
| `chalkboard` | Colorful chalk on black board, educational |
| `study-notes` | Realistic handwritten photo style, blue pen + red annotations + yellow highlighter |
| `screen-print` | Bold poster art, halftone textures, limited colors, symbolic storytelling |
| `sketch-notes` | Hand-drawn educational infographic, macaron pastels on warm cream, wobble lines |

Per-style specifications: `references/presets/<style>.md`.

## Layouts (8)

| Layout | Description |
|--------|-------------|
| `sparse` (Default) | 1-2 points, maximum impact |
| `balanced` | 3-4 points, standard |
| `dense` | 5-8 points, knowledge-card style |
| `list` | Enumeration / ranking (4-7 items) |
| `comparison` | Side-by-side contrast |
| `flow` | Process / timeline (3-6 steps) |
| `mindmap` | Center-radial (4-8 branches) |
| `quadrant` | Four-quadrant / circular sections |

Layout specs: `references/elements/canvas.md`.

## Palettes (optional override)

Replaces the style's colors while keeping rendering rules (line treatment, textures) intact.

| Palette | Background | Zone Colors | Accent | Feel |
|---------|------------|-------------|--------|------|
| `macaron` | Warm cream #F5F0E8 | Blue #A8D8EA, Lavender #D5C6E0, Mint #B5E5CF, Peach #F8D5C4 | Coral #E8655A | Soft, educational |
| `warm` | Soft peach #FFECD2 | Orange #ED8936, Terracotta #C05621, Golden #F6AD55, Rose #D4A09A | Sienna #A0522D | Earth tones, cozy |
| `neon` | Dark purple #1A1025 | Cyan #00F5FF, Magenta #FF00FF, Green #39FF14, Pink #FF6EC7 | Yellow #FFFF00 | High-energy, futuristic |

Palette specs: `references/palettes/<palette>.md`.

## Presets (style + layout shortcuts)

Quick-start combos, grouped by scenario. Use `--preset <name>` or recommend during Step 2.

**Knowledge & Learning**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `knowledge-card` | notion | dense | 干货知识卡、概念科普 |
| `checklist` | notion | list | 清单、排行榜 |
| `concept-map` | notion | mindmap | 概念图、知识脉络 |
| `swot` | notion | quadrant | SWOT 分析、四象限 |
| `tutorial` | chalkboard | flow | 教程步骤、操作流程 |
| `classroom` | chalkboard | balanced | 课堂笔记、知识讲解 |
| `study-guide` | study-notes | dense | 学习笔记、考试重点 |
| `hand-drawn-edu` | sketch-notes | flow | 手绘教程、流程图解 |
| `sketch-card` | sketch-notes | dense | 手绘知识卡 |
| `sketch-summary` | sketch-notes | balanced | 手绘总结、图文笔记 |

**Lifestyle & Sharing**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `cute-share` | cute | balanced | 少女风分享、日常种草 |
| `girly` | cute | sparse | 甜美封面、氛围感 |
| `cozy-story` | warm | balanced | 生活故事、情感分享 |
| `product-review` | fresh | comparison | 产品对比、测评 |
| `nature-flow` | fresh | flow | 健康流程、自然主题 |

**Impact & Opinion**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `warning` | bold | list | 避坑指南、重要提醒 |
| `versus` | bold | comparison | 正反对比 |
| `clean-quote` | minimal | sparse | 金句、极简封面 |
| `pro-summary` | minimal | balanced | 专业总结、商务内容 |

**Trend & Entertainment**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `retro-ranking` | retro | list | 复古排行、经典盘点 |
| `throwback` | retro | balanced | 怀旧分享 |
| `pop-facts` | pop | list | 趣味冷知识 |
| `hype` | pop | sparse | 炸裂封面、惊叹分享 |

**Poster & Editorial**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `poster` | screen-print | sparse | 海报风封面、影评书评 |
| `editorial` | screen-print | balanced | 观点文章、文化评论 |
| `cinematic` | screen-print | comparison | 电影对比、戏剧张力 |

Full prompt-fragment definitions: `references/style-presets.md`.

## Auto-Selection

Match content signals to the best combo. First row whose keywords appear wins; fall back to `cute-share` if nothing matches.

| Signals in source | Style | Layout | Recommended preset |
|-------------------|-------|--------|--------------------|
| beauty, fashion, cute, girl, pink | `cute` | sparse/balanced | `cute-share`, `girly` |
| health, nature, fresh, organic | `fresh` | balanced/flow | `product-review`, `nature-flow` |
| life, story, emotion, warm | `warm` | balanced | `cozy-story` |
| warning, important, must, critical | `bold` | list/comparison | `warning`, `versus` |
| professional, business, elegant | `minimal` | sparse/balanced | `clean-quote`, `pro-summary` |
| classic, vintage, traditional | `retro` | balanced | `throwback`, `retro-ranking` |
| fun, exciting, wow, amazing | `pop` | sparse/list | `hype`, `pop-facts` |
| knowledge, concept, productivity, SaaS | `notion` | dense/list | `knowledge-card`, `checklist` |
| education, tutorial, learning, classroom | `chalkboard` | balanced/dense | `tutorial`, `classroom` |
| notes, handwritten, study guide, realistic | `study-notes` | dense/list/mindmap | `study-guide` |
| movie, poster, opinion, editorial, cinematic | `screen-print` | sparse/comparison | `poster`, `editorial`, `cinematic` |
| hand-drawn, infographic, workflow, 手绘，图解 | `sketch-notes` | flow/balanced/dense | `hand-drawn-edu`, `sketch-card`, `sketch-summary` |

## Style × Layout Matrix

Compatibility scores (✓✓ highly recommended, ✓ works well, ✗ avoid). Use when the user picks a non-default combo and you want to flag a poor match.

|              | sparse | balanced | dense | list | comparison | flow | mindmap | quadrant |
|--------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cute         | ✓✓ | ✓✓ | ✓  | ✓✓ | ✓  | ✓  | ✓  | ✓  |
| fresh        | ✓✓ | ✓✓ | ✓  | ✓  | ✓  | ✓✓ | ✓  | ✓  |
| warm         | ✓✓ | ✓✓ | ✓  | ✓  | ✓✓ | ✓  | ✓  | ✓  |
| bold         | ✓✓ | ✓  | ✓  | ✓✓ | ✓✓ | ✓  | ✓  | ✓✓ |
| minimal      | ✓✓ | ✓✓ | ✓✓ | ✓  | ✓  | ✓  | ✓  | ✓  |
| retro        | ✓✓ | ✓✓ | ✓  | ✓✓ | ✓  | ✓  | ✓  | ✓  |
| pop          | ✓✓ | ✓✓ | ✓  | ✓✓ | ✓✓ | ✓  | ✓  | ✓  |
| notion       | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓✓ |
| chalkboard   | ✓✓ | ✓✓ | ✓✓ | ✓✓ | ✓  | ✓✓ | ✓✓ | ✓  |
| study-notes  | ✗  | ✓  | ✓✓ | ✓✓ | ✓  | ✓  | ✓✓ | ✓  |
| screen-print | ✓✓ | ✓✓ | ✗  | ✓  | ✓✓ | ✓  | ✗  | ✓✓ |
| sketch-notes | ✓  | ✓✓ | ✓✓ | ✓✓ | ✓  | ✓✓ | ✓✓ | ✓  |

## Outline Strategies

Three differentiated approaches — each produces a structurally different outline. The workflow recommends one; Path C generates all three and lets the user choose.

| Strategy | Concept | Best for | Structure |
|----------|---------|----------|-----------|
| **A — Story-Driven** | Personal experience as the thread, emotional resonance first | Reviews, personal shares, transformation | Hook → Problem → Discovery → Experience → Conclusion |
| **B — Information-Dense** | Value-first, efficient information delivery | Tutorials, comparisons, checklists | Core conclusion → Info card → Pros/Cons → Recommendation |
| **C — Visual-First** | Visual impact as core, minimal text | High-aesthetic products, lifestyle, mood content | Hero image → Detail shots → Lifestyle scene → CTA |

## Reference Images

User-supplied refs are **separate from** the internal "image-1 as anchor" chain (Step 3) — they layer on top of it.

**Intake**: via `--ref <files...>` or paths pasted in conversation.
- File path → copy to `refs/NN-ref-{slug}.{ext}`
- Pasted with no path → ask for the path, or extract style traits as a text fallback

**Usage modes** (per reference):

| Usage | Effect |
|-------|--------|
| `direct` | Pass the file through `$skillsvc-image reference --image` (typically on image 1 only, so the anchor propagates through the chain) |
| `style` | Extract style traits and append to every card's prompt body |
| `palette` | Extract hex colors and append to every card's prompt body |

Record refs in each affected card's prompt frontmatter:

```yaml
references:
  - ref_id: 01
    filename: 01-ref-brand.png
    usage: direct
```

At generation time: verify files exist. If image 1 has `usage: direct`, call `$skillsvc-image reference` with one `--image` per user reference; it becomes the chain anchor. Images 2+ use only image 1 through `reference --image` — do NOT re-stack user refs on top. For `style`/`palette`, embed extracted traits in every prompt.

## File Layout

```
image-cards/{topic-slug}/
├── source-references/               # optional reference material
├── post.md                          # completed XHS or Tietu copy
├── analysis.md
├── outline-strategy-{a,b,c}.md    # Path C only
├── outline.md
├── prompts/NN-{type}-{slug}.md
├── NN-{type}-{slug}.png
└── refs/                          # only if --ref used
```

**Slug**: 2-4 words, kebab-case. "AI 工具推荐" → `ai-tools-recommend`. On collision, append `-YYYYMMDD-HHMMSS`.

**Backup rule** (applies throughout): before overwriting any file — source, outline, prompt, image — rename the existing one to `<name>-backup-YYYYMMDD-HHMMSS.<ext>`. This protects user edits.

## Workflow

```
- [ ] Step 0: Load EXTEND.md ⛔ BLOCKING (interactive only)
- [ ] Step 1: Write or prepare platform copy → post.md; analyze → analysis.md
- [ ] Step 2: Smart Confirm ⚠️ REQUIRED (Path A / B / C)
- [ ] Step 3: Generate images
- [ ] Step 4: Completion report
```

### Step 0: Load EXTEND.md ⛔ BLOCKING

Check these paths in order; first hit wins:

| Path | Scope |
|------|-------|
| `.baoyu-skills/baoyu-xhs-images/EXTEND.md` | Project |
| `${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/baoyu-xhs-images/EXTEND.md` | XDG |
| `$HOME/.baoyu-skills/baoyu-xhs-images/EXTEND.md` | User home |

- **Found** → read, parse, print a summary (style / layout / watermark / language), continue.
- **Not found + interactive** → run first-time setup (see `references/config/first-time-setup.md`) and save before anything else. Do NOT analyze content or ask style questions until preferences exist — this keeps first-run behavior predictable.
- **Not found + `--yes`** → skip setup, use built-in defaults (no watermark, style/layout auto-selected, language from content). Do not prompt, do not create EXTEND.md.

**EXTEND.md keys**: watermark, preferred style/layout, custom style definitions, language preference, generation batch size. Schema: `references/config/preferences-schema.md`.

### Step 1: Prepare Image Context → `post.md` + `analysis.md`

1. Determine whether the requested final format is Xiaohongshu or Tietu. Adapt title, opening hook, paragraph rhythm, tags, call to action, and information density to that target; do not infer the target from a reference source.
2. Prepare the source material:
   - Topic only + illustrated post request → prepare original platform copy for the card series.
   - References supplied → extract useful angles, structure, tone, facts, and visual rhythm, then create new copy. Save references under `source-references/` when they are files.
   - Existing final copy → preserve it unless the user asks for rewriting or polishing.
3. Save the supporting platform copy to `post.md` when the requested deliverable includes copy. For cards-only requests, this may be a concise internal content draft rather than a separate user-facing article. Do not fabricate personal experiences, product usage results, statistics, testimonials, or guarantees.
4. Analyze `post.md` using `references/workflows/analysis-framework.md`: content type, hook potential, audience, engagement signals, visual opportunity map, and swipe flow.
5. Detect the content language and choose a recommended image count from 2-10.
6. Auto-recommend strategy + style + layout + palette using the **Auto-Selection** table above.
7. Save the analysis to `analysis.md`, then use `post.md` as the canonical content source for the outline and card prompts.

### Step 2: Smart Confirm ⚠️ REQUIRED

**Hard gate**: this step is mandatory per the [Confirmation Policy](#confirmation-policy) — Step 3 cannot start until the user confirms here (or explicitly opts out with `--yes` / equivalent wording in the current request).

Goal: present the auto-recommended plan and let the user confirm or adjust. Skip this step entirely under `--yes` — proceed with Path A using the analysis and any CLI overrides.

**Display summary** before asking:

```
📋 内容分析
  主题：[topic] | 类型：[content_type]
  要点：[key points]
  受众：[audience]

🎨 推荐方案（自动匹配）
  策略：[A/B/C] [name]（[reason]）
  风格：[style] · 布局：[layout] · 配色：[palette or 默认] · 预设：[preset]
  图片：[N]张（封面+[N-2]内容+结尾）
  元素：[background] / [decorations] / [emphasis]
```

Then ask one question — three paths. Verbatim option copy: `references/confirmation.md`.

**Path A — Quick confirm** (trust auto-recommendation): generate a single outline using the recommended strategy + style → save to `outline.md` → Step 3.

**Path B — Customize**: ask five questions (strategy/style, layout, palette, count, optional notes) with the recommendation pre-filled — blanks keep the recommendation. Generate one outline with the user's choices → `outline.md` → Step 3. See `references/confirmation.md`.

**Path C — Detailed mode**: two sub-confirmations.

- *Step 2a — Content understanding*: ask selling points (multi-select), audience, style preference (authentic / professional / aesthetic / auto), optional context. Update `analysis.md`.
- *Step 2b — Three outline variants*: generate `outline-strategy-a.md`, `outline-strategy-b.md`, `outline-strategy-c.md`. Each MUST have a different structure AND a different recommended style — include `style_reason` in the frontmatter. Page-count heuristic: A ~4-6, B ~3-5, C ~3-4. Template: `references/workflows/outline-template.md`; frontmatter example in `references/confirmation.md`.
- *Step 2c — Selection*: ask three questions (outline A/B/C/Combined, style, visual elements). Save selected/merged outline to `outline.md` → Step 3.

### Step 3: Generate Images

With confirmed outline + style + layout + palette:

**Visual consistency — image-1 anchor chain**: character / mascot / color rendering drifts between calls unless you anchor them. Generate image 1 first with `$skillsvc-image generate` (or `reference` when the user supplied direct references), then pass image 1 through `$skillsvc-image reference --image` to every subsequent image. Reference mode creates a new card and composition; it does not edit the cover.

Generation flow:

1. Write the full prompt for every image to `prompts/NN-{type}-{slug}.md` in the user's preferred language (backup rule applies), then verify all selected prompt files exist.
2. Generate **image 1** first with `--aspect-ratio 3:4 --image-size 2K`; backup rule applies to the PNG file. This establishes the anchor.
3. Build a task list for **images 2+** using `$skillsvc-image reference --image <path-to-image-01.png>` with the same dimensions.
4. Dispatch images 2+ in batches per the `## Batch Generation Policy`: runtime parallel tool calls first, sequential execution as fallback.
5. Report progress after each completed image. On failure, retry only the failed item once from the same saved prompt file.

**Watermark** (if enabled in EXTEND.md): append to the generation prompt:

```
Include a subtle watermark "[content]" positioned at [position].
The watermark should be legible but not distracting.
```

See `references/config/watermark-guide.md`.

**Backend call**: always use `$skillsvc-image`. Prompt files MUST exist before invoking it. Its CLI has no multi-image batch endpoint, so use parallel CLI calls for images 2+ when the runtime supports parallel execution.

**Session management**: keep one returned session JSON per card. Never reuse one edit session across different cards. For later changes, update that card's prompt file first, then call `$skillsvc-image edit --session <card-session.json>`.

### Step 4: Completion Report

```
Image Card Series Complete!

Topic: [topic]
Mode: [Quick / Custom / Detailed]
Strategy: [A/B/C/Combined]
Style: [name]
Palette: [name or "default"]
Layout: [name or "varies"]
Location: [directory]
Images: N total

✓ analysis.md
✓ post.md
✓ outline.md
✓ outline-strategy-a/b/c.md (detailed mode only)

- 01-cover-[slug].png ✓ Cover (sparse)
- 02-content-[slug].png ✓ Content (balanced)
- ...
- NN-ending-[slug].png ✓ Ending (sparse)
```

## Content Breakdown Principles

| Position | Purpose | Typical layout |
|----------|---------|----------------|
| Cover (image 1) | Hook + visual impact | `sparse` |
| Content (middle) | Core value per image | `balanced` / `dense` / `list` / `comparison` / `flow` |
| Ending (last) | CTA / summary | `sparse` or `balanced` |

For the style × layout compatibility matrix, see the **Style × Layout Matrix** above.

## Image Modification

| Action | How |
|--------|-----|
| Edit | Update `prompts/NN-{type}-{slug}.md` **first**, then call `$skillsvc-image edit` with that card's session JSON |
| Add | Specify position, create prompt, generate, renumber subsequent files `NN+1`, update outline |
| Delete | Remove files, renumber subsequent `NN-1`, update outline |

Always update the prompt file before regenerating — it's the source of truth and makes changes reproducible.

Text correction policy:

- If a card's title, body copy, tags, or any other rendered text is misspelled, garbled, hard to read, or visually weak, do not patch the bitmap with code.
- For text-correction regenerations, write a new prompt file and a new output path so the flawed candidate is preserved for comparison.
- Post-processing is limited to crop, resize, compression, or format conversion that does not alter text or the main composition.

## References

| File | Content |
|------|---------|
| `references/confirmation.md` | Verbatim AskUserQuestion copy for every confirmation path |
| `references/style-presets.md` | Full preset shortcut definitions |
| `references/presets/<style>.md` | Per-style element definitions |
| `references/palettes/<name>.md` | Per-palette color definitions |
| `references/elements/canvas.md` | Aspect ratios, safe zones, grid layouts |
| `references/elements/image-effects.md` | Cutout, stroke, filters |
| `references/elements/typography.md` | Decorated text, tags, text direction |
| `references/elements/decorations.md` | Emphasis marks, backgrounds, doodles, frames |
| `references/workflows/analysis-framework.md` | Content analysis framework |
| `references/workflows/outline-template.md` | Outline template with layout guide |
| `references/workflows/prompt-assembly.md` | Prompt assembly guide |
| `references/config/preferences-schema.md` | EXTEND.md schema |
| `references/config/first-time-setup.md` | First-time setup flow |
| `references/config/watermark-guide.md` | Watermark configuration |

## Notes

- Auto-retry once on generation failure before reporting an error.
- For sensitive public figures, use stylized cartoon alternatives.
- Smart Confirm (Step 2) is required; Detailed mode adds a second confirmation (2a + 2c).

## Changing Preferences

EXTEND.md lives at the first matching path listed in Step 0. Three ways to change it:

- **Edit directly** — open EXTEND.md and change fields. Full schema: `references/config/preferences-schema.md`.
- **Reconfigure interactively** — delete EXTEND.md (or ask "reconfigure baoyu-xhs-images preferences" / "重新配置"). The next run re-triggers first-time setup.
- **Common one-line edits**:
  - `generation_batch_size: 4` — default number of images to render concurrently when the backend/runtime supports batch or parallel generation.
  - `preferred_style: notion`, `preferred_layout: dense`, `preferred_palette: macaron`, `language: zh`.
  - `watermark.enabled: true` + `watermark.content: "@handle"` — add a watermark.
