# Next SEKAI Sonolus Engine

A new Project Sekai inspired engine for [Sonolus](https://sonolus.com).

## Official Resources

Server: https://coconut.sonolus.com/next-sekai/
Editor: https://next-sekai-editor.sonolus.com/

## Quick Dev Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Run `uv sync`.
3. Add resources (full exported scp files) such as skins and levels to the `/resources` folder.
4. [Ensure your venv is activated](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment).
5. Run `sonolus-py dev`.

## Custom Resources

### Skin Sprites

For each role below, the engine picks the first available sprite in the listed
order. Earlier entries take precedence over later ones, and `->` separates
fallbacks from highest to lowest priority.

Shorthand used in the tables:

- `{A, B, C}` expands to one sprite per listed value, e.g.
  `Holodori Normal Note {Left, Middle, Right}` = `Holodori Normal Note Left`,
  `Holodori Normal Note Middle`, `Holodori Normal Note Right`.
- `{1..6}` expands to a range, e.g.
  `Holodori Flick Arrow {1..6}` = `Holodori Flick Arrow 1` through
  `Holodori Flick Arrow 6`.

#### Stage

| Role                | Sprite                         |
| ------------------- | ------------------------------ |
| Stage Background    | `Holodori Stage Background`    |
| Stage               | `Holodori Stage` (optional)    |
| Stage Judgment Line | `Holodori Stage Judgment Line` |

#### Lines

| Role                  | Precedence                                                            |
| --------------------- | --------------------------------------------------------------------- |
| Measure Line          | `Holodori Measure Line` -> `SIMULTANEOUS_CONNECTION_NEUTRAL`          |
| Skill Activation Line | `Holodori Skill Activation Line` -> `SIMULTANEOUS_CONNECTION_NEUTRAL` |

#### Note Bodies

`Holodori Note Icon` is drawn over every visible non-tick note using a fixed-size, perspective-aware layout.

| Note Type            | Bucket Icon                   | Render Style | Body Precedence                                                              |
| -------------------- | ----------------------------- | ------------ | ---------------------------------------------------------------------------- |
| Tap                  | `Holodori Normal Note Middle` | Normal       | `Holodori Normal Note {Left, Middle, Right}` -> `NOTE_HEAD_CYAN`             |
| Offbeat Tap          | `Holodori Normal Note Middle` | Normal       | `Holodori Offbeat Note {Left, Middle, Right}` -> `NOTE_HEAD_CYAN`            |
| Slide                | `Holodori Long Note Middle`   | Normal       | `Holodori Long Note {Left, Middle, Right}` -> `NOTE_HEAD_GREEN`              |
| Flick                | `Holodori Flick Note Middle`  | Normal       | `Holodori Flick Note {Left, Middle, Right}` -> `NOTE_HEAD_RED`               |
| Critical             | `Holodori Accent Note Middle` | Normal       | `Holodori Accent Note {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`           |
| Critical Slide       | `Holodori Accent Note Middle` | Normal       | `Holodori Accent Note {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`           |
| Critical Flick       | `Holodori Accent Note Middle` | Normal       | `Holodori Accent Note {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`           |
| Trace                | `Holodori Note Icon`          | Normal       | `Holodori Long Note {Left, Middle, Right}` -> `NOTE_HEAD_GREEN`              |
| Trace Flick          | `Holodori Flick Note Middle`  | Normal       | `Holodori Flick Note {Left, Middle, Right}` -> `NOTE_HEAD_RED`               |
| Critical Trace       | `Holodori Note Icon`          | Normal       | `Holodori Accent Note {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`           |
| Critical Trace Flick | `Holodori Accent Note Middle` | Normal       | `Holodori Accent Note {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`           |
| Damage               | `Holodori Damage Note Basic`  | Normal       | `Holodori Damage Note {Left, Middle, Right}` -> `Holodori Damage Note Basic` |

The offbeat body is used only by `NormalTapNote` entities whose beat is not an integer. Flick, long, and accent note families keep their regular body mappings.

#### Relay Notes

| Tick Type     | Precedence                                    |
| ------------- | --------------------------------------------- |
| Normal Tick   | `Holodori Normal Relay` -> `NOTE_TICK_GREEN`  |
| Critical Tick | `Holodori Accent Relay` -> `NOTE_TICK_YELLOW` |

#### Active Slide Connectors

| Connector | Precedence                                                  |
| --------- | ----------------------------------------------------------- |
| Normal    | `Holodori Long Normal` -> `NOTE_CONNECTION_GREEN_SEAMLESS`  |
| Critical  | `Holodori Long Accent` -> `NOTE_CONNECTION_YELLOW_SEAMLESS` |

#### Slots & Slot Glows

| Note Type               | Slot                   | Slot Glow                   |
| ----------------------- | ---------------------- | --------------------------- |
| Tap                     | `Holodori Slot Normal` | `Holodori Slot Glow Normal` |
| Slide                   | `Holodori Slot Long`   | `Holodori Slot Glow Long`   |
| Flick                   | `Holodori Slot Flick`  | `Holodori Slot Glow Flick`  |
| Critical                | `Holodori Slot Accent` | `Holodori Slot Glow Accent` |
| Critical Slide          | `Holodori Slot Accent` | `Holodori Slot Glow Accent` |
| Critical Flick          | `Holodori Slot Accent` | `Holodori Slot Glow Accent` |
| Active Slide (Normal)   | --                     | `Holodori Slot Glow Long`   |
| Active Slide (Critical) | --                     | `Holodori Slot Glow Accent` |

#### Flick Arrows

| Note Family                           | Precedence                                                          |
| ------------------------------------- | ------------------------------------------------------------------- |
| Flick / Trace Flick                   | `Holodori Flick Arrow {1..6}` -> `DIRECTIONAL_MARKER_RED`           |
| Critical Flick / Critical Trace Flick | `Holodori Flick Arrow Accent {1..6}` -> `DIRECTIONAL_MARKER_YELLOW` |

#### Guides

| Color   | Precedence                                                     |
| ------- | -------------------------------------------------------------- |
| Green   | `Holodori Guide Green` -> `NOTE_CONNECTION_GREEN_SEAMLESS`     |
| Yellow  | `Holodori Guide Yellow` -> `NOTE_CONNECTION_YELLOW_SEAMLESS`   |
| Red     | `Holodori Guide Red` -> `NOTE_CONNECTION_RED_SEAMLESS`         |
| Purple  | `Holodori Guide Magenta` -> `NOTE_CONNECTION_PURPLE_SEAMLESS`  |
| Cyan    | `Holodori Guide Cyan` -> `NOTE_CONNECTION_CYAN_SEAMLESS`       |
| Blue    | `Holodori Guide Blue` -> `NOTE_CONNECTION_BLUE_SEAMLESS`       |
| Neutral | `Holodori Guide Neutral` -> `NOTE_CONNECTION_NEUTRAL_SEAMLESS` |
| Black   | `Holodori Guide Black` -> `NOTE_CONNECTION_NEUTRAL_SEAMLESS`   |

### Effect Clips

For each role below, the engine picks the first available effect clip in the
listed order.

| Role                                  | Precedence                                       |
| ------------------------------------- | ------------------------------------------------ |
| Stage                                 | `STAGE`                                          |
| Normal Tap / Long Head Perfect        | `PERFECT`                                        |
| Normal Tap / Long Head Great          | `GREAT`                                          |
| Normal Tap / Long Head Good           | `GOOD`                                           |
| Normal Trace (non-miss)               | `PERFECT`                                        |
| Flick / Trace Flick (non-miss)        | `PERFECT_ALTERNATIVE`                            |
| Normal Hold                           | `HOLD`                                           |
| Normal Relay (non-miss)               | `Holodori Relay` -> `PERFECT`                    |
| Accent Tap / Accent Trace (non-miss)  | `Holodori Accent Tap` -> `PERFECT`               |
| Accent Flick / Trace Flick (non-miss) | `Holodori Accent Flick` -> `PERFECT_ALTERNATIVE` |
| Accent Hold                           | `Holodori Accent Hold` -> `HOLD`                 |
| Accent Relay (non-miss)               | `Holodori Accent Tick` -> `PERFECT`              |
| Damage Miss                           | `GOOD`                                           |

### Particle Effects

For each role below, the engine picks the first available particle in the
listed order. Entries without an arrow are optional and produce no particle
when absent.

#### Notes

| Role               | Precedence                                                               |
| ------------------ | ------------------------------------------------------------------------ |
| Basic Lane         | `LANE_LINEAR`                                                            |
| Normal Circular    | `Holodori Normal Note Circular` -> `NOTE_CIRCULAR_TAP_CYAN`              |
| Normal Linear      | `Holodori Normal Note Linear` -> `NOTE_LINEAR_TAP_CYAN`                  |
| Normal Lane        | `Holodori Note Lane Linear`                                              |
| Normal Slot        | `Holodori Slot Normal Linear`                                            |
| Long Circular      | `Holodori Long Note Circular` -> `NOTE_CIRCULAR_TAP_GREEN`               |
| Long Linear        | `Holodori Long Note Linear` -> `NOTE_LINEAR_TAP_GREEN`                   |
| Long Lane          | `Holodori Slide Lane Linear` -> `Holodori Note Lane Linear`              |
| Long Slot          | `Holodori Slot Long Linear`                                              |
| Flick Circular     | `Holodori Flick Note Circular` -> `NOTE_CIRCULAR_TAP_RED`                |
| Flick Linear       | `Holodori Flick Note Linear` -> `NOTE_LINEAR_TAP_RED`                    |
| Flick Directional  | `Holodori Flick Note Directional` -> `NOTE_LINEAR_ALTERNATIVE_RED`       |
| Flick Lane         | `Holodori Flick Lane Linear`                                             |
| Flick Slot         | `Holodori Slot Flick Linear`                                             |
| Accent Circular    | `Holodori Accent Note Circular` -> `NOTE_CIRCULAR_TAP_YELLOW`            |
| Accent Linear      | `Holodori Accent Note Linear` -> `NOTE_LINEAR_TAP_YELLOW`                |
| Accent Directional | `Holodori Accent Note Directional` -> `NOTE_LINEAR_ALTERNATIVE_YELLOW`   |
| Accent Lane        | `Holodori Critical Lane Linear`                                          |
| Accent Long Lane   | `Holodori Critical Slide Lane Linear` -> `Holodori Critical Lane Linear` |
| Accent Flick Lane  | `Holodori Critical Flick Lane Linear`                                    |
| Accent Slot        | `Holodori Slot Accent Linear`                                            |
| Normal Relay       | `Holodori Normal Relay` -> `NOTE_CIRCULAR_ALTERNATIVE_GREEN`             |
| Accent Relay       | `Holodori Accent Relay` -> `NOTE_CIRCULAR_ALTERNATIVE_YELLOW`            |
| Damage Circular    | `Holodori Damage Note Circular` -> `NOTE_CIRCULAR_TAP_PURPLE`            |
| Damage Linear      | `Holodori Damage Note Linear` -> `NOTE_LINEAR_TAP_PURPLE`                |

#### Active Slide Connectors

| Role                | Precedence                                                     |
| ------------------- | -------------------------------------------------------------- |
| Normal Circular     | `Holodori Long Normal Circular` -> `NOTE_CIRCULAR_HOLD_GREEN`  |
| Normal Linear       | `Holodori Long Normal Linear` -> `NOTE_LINEAR_HOLD_GREEN`      |
| Normal Trail Linear | `Holodori Long Normal Trail Linear`                            |
| Normal Slot Linear  | `Holodori Long Normal Slot Linear`                             |
| Accent Circular     | `Holodori Long Accent Circular` -> `NOTE_CIRCULAR_HOLD_YELLOW` |
| Accent Linear       | `Holodori Long Accent Linear` -> `NOTE_LINEAR_HOLD_YELLOW`     |
| Accent Trail Linear | `Holodori Long Accent Trail Linear`                            |
| Accent Slot Linear  | `Holodori Long Accent Slot Linear`                             |
