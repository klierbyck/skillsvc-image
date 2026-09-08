# Style Presets

本文件中的 `--preset`、`--style`、`--layout` 和 `--palette` 只是技能在规划视觉方案时使用的快捷写法，不是 `scripts/generate_image.py` 的 CLI 参数。应先把选择结果展开到完整 prompt，再由父技能调用生图 CLI。

`--preset X` expands to a style + layout + optional palette combination. Users can override any dimension.

| --preset | Style | Layout | Palette |
|----------|-------|--------|---------|
| `knowledge-card` | `notion` | `dense` | |
| `checklist` | `notion` | `list` | |
| `concept-map` | `notion` | `mindmap` | |
| `swot` | `notion` | `quadrant` | |
| `tutorial` | `chalkboard` | `flow` | |
| `classroom` | `chalkboard` | `balanced` | |
| `study-guide` | `study-notes` | `dense` | |
| `cute-share` | `cute` | `balanced` | |
| `girly` | `cute` | `sparse` | |
| `cozy-story` | `warm` | `balanced` | |
| `product-review` | `fresh` | `comparison` | |
| `nature-flow` | `fresh` | `flow` | |
| `warning` | `bold` | `list` | |
| `versus` | `bold` | `comparison` | |
| `clean-quote` | `minimal` | `sparse` | |
| `pro-summary` | `minimal` | `balanced` | |
| `retro-ranking` | `retro` | `list` | |
| `throwback` | `retro` | `balanced` | |
| `pop-facts` | `pop` | `list` | |
| `hype` | `pop` | `sparse` | |
| `poster` | `screen-print` | `sparse` | |
| `editorial` | `screen-print` | `balanced` | |
| `cinematic` | `screen-print` | `comparison` | |
| `hand-drawn-edu` | `sketch-notes` | `flow` | `macaron` |
| `sketch-card` | `sketch-notes` | `dense` | `macaron` |
| `sketch-summary` | `sketch-notes` | `balanced` | `macaron` |

Empty Palette = use style's built-in colors (or style's `default_palette` if defined in frontmatter).

## Override Examples

- `--preset knowledge-card --style chalkboard` = chalkboard style with dense layout
- `--preset poster --layout quadrant` = screen-print style with quadrant layout
- `--preset hand-drawn-edu --palette warm` = sketch-notes style with flow layout, warm palette instead of macaron
- `--style notion --palette macaron` = notion rendering rules with macaron colors

Explicit `--style`/`--layout`/`--palette` flags always override preset values.
