# Next SEKAI Sonolus Engine

A new Project Sekai inspired engine for [Sonolus](https://sonolus.com).

## Official Resources

Server: https://coconut.sonolus.com/next-sekai/  
Editor: https://next-sekai-editor.sonolus.com/

## Quick Dev Setup

Requires Python 3.15 or newer.

1. Install [uv](https://docs.astral.sh/uv/).
2. Run `uv sync`.
3. Add resources (full exported scp files) such as skins and levels to the `/resources` folder.
4. [Ensure your venv is activated](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment).
5. Run `sonolus-py dev`.

## Custom Resources

`<Color>` = `{Neutral, Red, Green, Blue, Yellow, Purple, Cyan, Black}`.

### Skin Sprites

For each role below, the engine picks the first available sprite in the listed
order. Earlier entries take precedence over later ones, and `->` separates
fallbacks from highest to lowest priority.

Shorthand used in the tables:

- `{A, B, C}` expands to one sprite per listed value, e.g.
  `Sekai Normal Note {Left, Middle, Right}` = `Sekai Normal Note Left`,
  `Sekai Normal Note Middle`, `Sekai Normal Note Right`.
- `{1..6}` expands to a range, e.g.
  `Sekai Flick Arrow Up {1..6}` = `Sekai Flick Arrow Up 1` through
  `Sekai Flick Arrow Up 6`.

#### Stage

| Role                     | Sprite                                                                     |
|--------------------------|----------------------------------------------------------------------------|
| Stage                    | `Sekai Stage` (optional)                                                   |
| Stage Border             | `Sekai Stage Border`                                                       |
| Lane Background          | `Sekai Lane Background <Color>` -> `Sekai Lane Background`                 |
| Lane Divider             | `Sekai Lane Divider`                                                       |
| Lane Background Preview  | `Sekai Lane Background Preview <Color>` -> `Sekai Lane Background Preview` |
| Lane Divider Preview     | `Sekai Lane Divider Preview`                                               |
| Stage Border Preview     | `Sekai Stage Border Preview`                                               |
| Judgment Line Background | `Sekai Judgment Background <Color>` -> `Sekai Judgment Background`         |
| Judgment Gradient        | `Sekai Judgment Gradient <Color>`                                          |
| Judgment Edge            | `Sekai Judgment Edge <Color>`                                              |
| Judgment Single Line     | `Sekai Judgment Single Line <Color>` -> `Sekai Judgment Edge <Color>`      |
| Judgment Edge Left       | `Sekai Judgment Edge Left <Color>` -> `Sekai Judgment Edge <Color>`        |
| Judgment Center          | `Sekai Judgment Center <Color>`                                            |

#### Note Bodies

`Holodori Note Icon` is drawn over every visible non-tick note using a fixed-size, perspective-aware layout.

| Note Type                 | Bucket Icon                     | Render Style | Body Precedence                                                                                                                                                                                                                               |
|---------------------------|---------------------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tap                       | `Sekai Normal Note Basic`               | Normal       | `Sekai Normal Note {Left, Middle, Right}` -> `Sekai Note Cyan {Left, Middle, Right}` -> `NOTE_HEAD_CYAN`                                                                                                                                              |
| Slide                     | `Sekai Slide Note Basic`                | Normal       | `Sekai Slide Note {Left, Middle, Right}` -> `Sekai Note Green {Left, Middle, Right}` -> `NOTE_HEAD_GREEN`                                                                                                                                             |
| Flick                     | `Sekai Flick Note Basic`                | Normal       | `Sekai Flick Note {Left, Middle, Right}` -> `Sekai Note Red {Left, Middle, Right}` -> `NOTE_HEAD_RED`                                                                                                                                                 |
| Critical                  | `Sekai Critical Note Basic`             | Normal       | `Sekai Critical Note {Left, Middle, Right}` -> `Sekai Note Yellow {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`                                                                                                                                        |
| Critical Slide            | `Sekai Critical Slide Note Basic`       | Normal       | `Sekai Critical Slide Note {Left, Middle, Right}` -> `Sekai Critical Note {Left, Middle, Right}` -> `Sekai Note Yellow {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`                                                                                   |
| Critical Flick            | `Sekai Critical Flick Note Basic`       | Normal       | `Sekai Critical Flick Note {Left, Middle, Right}` -> `Sekai Critical Note {Left, Middle, Right}` -> `Sekai Note Yellow {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`                                                                                   |
| Trace                     | `Holodori Note Icon`            | Normal       | `Sekai Slide Note {Left, Middle, Right}` -> `Sekai Note Green {Left, Middle, Right}` -> `NOTE_HEAD_GREEN`                                                                                                                                      |
| Trace Flick               | `Sekai Note Red Middle`         | Normal       | `Sekai Note Red {Left, Middle, Right}` -> `NOTE_HEAD_RED`                                                                                                                                                                                       |
| Critical Trace            | `Holodori Note Icon`            | Normal       | `Sekai Critical Slide Note {Left, Middle, Right}` -> `Sekai Critical Note {Left, Middle, Right}` -> `Sekai Note Yellow {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`                                                                             |
| Critical Trace Flick      | `Sekai Note Yellow Middle`      | Normal       | `Sekai Note Yellow {Left, Middle, Right}` -> `NOTE_HEAD_YELLOW`                                                                                                                                                                                |
| Damage                    | `Sekai Damage Note Basic`       | Normal       | `Sekai Damage Note {Left, Middle, Right}`                                                                                                                                                                                                      |

#### Slide Tick Diamonds

| Tick Type           | Precedence                                                                                     |
|---------------------|------------------------------------------------------------------------------------------------|
| Normal Slide Tick   | `Sekai Normal Slide Diamond` -> `Sekai Diamond Green` -> `NOTE_TICK_GREEN`                     |
| Critical Slide Tick | `Sekai Critical Slide Diamond` -> `Sekai Diamond Yellow` -> `NOTE_TICK_YELLOW`                 |

#### Active Slide Connectors

| Connector | Precedence                                                                                                                                                |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Normal    | `Sekai Normal Active Slide Connection {Normal, Active}` -> `Sekai Active Slide Connection {Green, Green Active}` -> `NOTE_CONNECTION_GREEN_SEAMLESS`      |
| Critical  | `Sekai Critical Active Slide Connection {Normal, Active}` -> `Sekai Active Slide Connection {Yellow, Yellow Active}` -> `NOTE_CONNECTION_YELLOW_SEAMLESS` |

#### Slots & Slot Glows

| Note Type               | Slot Precedence                                                                                                                              | Slot Glow Precedence                                                                                                                                                  |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tap                     | `Sekai Slot Normal` -> `Sekai Slot Cyan`                                                                                                     | `Sekai Slot Glow Normal` -> `Sekai Slot Glow Cyan`                                                                                                                    |
| Slide                   | `Sekai Slot Slide` -> `Sekai Slot Green`                                                                                                     | `Sekai Slot Glow Slide` -> `Sekai Slot Glow Green`                                                                                                                    |
| Flick                   | `Sekai Slot Flick` -> `Sekai Slot Red`                                                                                                       | `Sekai Slot Glow Flick` -> `Sekai Slot Glow Red`                                                                                                                      |
| Critical                | `Sekai Slot Critical` -> `Sekai Slot Yellow`                                                                                                 | `Sekai Slot Glow Critical` -> `Sekai Slot Glow Yellow`                                                                                                                |
| Critical Slide          | `Sekai Slot Critical Slide` -> `Sekai Slot Yellow Slider` -> `Sekai Slot Critical` -> `Sekai Slot Yellow`                                    | `Sekai Slot Glow Critical Slide` -> `Sekai Slot Glow Yellow Slider Tap` -> `Sekai Slot Glow Critical` -> `Sekai Slot Glow Yellow`                                     |
| Critical Flick          | `Sekai Slot Critical Flick` -> `Sekai Slot Yellow Flick` -> `Sekai Slot Critical` -> `Sekai Slot Yellow`                                     | `Sekai Slot Glow Critical Flick` -> `Sekai Slot Glow Yellow Flick` -> `Sekai Slot Glow Critical` -> `Sekai Slot Glow Yellow`                                          |
| Active Slide (Normal)   | --                                                                                                                                           | `Sekai Normal Slide Slot Glow` -> `Sekai Slot Glow Slide` -> `Sekai Slot Glow Green`                                                                                  |
| Active Slide (Critical) | --                                                                                                                                           | `Sekai Critical Slide Slot Glow` -> `Sekai Slot Glow Critical Slide` -> `Sekai Slot Glow Yellow Slider Tap` -> `Sekai Slot Glow Critical` -> `Sekai Slot Glow Yellow` |

| Connector   | Sprite                               |
|-------------|--------------------------------------|
| Green Hold  | `Sekai Slot Glow Green Slider Hold`  |
| Yellow Hold | `Sekai Slot Glow Yellow Slider Hold` |

#### Flick Arrows

| Note Family                            | Precedence                                                                                                      |
|----------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| Flick / Trace Flick                    | `Sekai Flick Arrow Up {1..6}` -> `Sekai Flick Arrow Red Up {1..6}` -> `DIRECTIONAL_MARKER_RED`                  |
| Critical Flick / Critical Trace Flick  | `Sekai Critical Flick Arrow Up {1..6}` -> `Sekai Flick Arrow Yellow Up {1..6}` -> `DIRECTIONAL_MARKER_YELLOW`  |

#### Guides

| Color   | Precedence                                                  |
|---------|-------------------------------------------------------------|
| Green   | `Sekai Guide Green` -> `NOTE_CONNECTION_GREEN_SEAMLESS`     |
| Yellow  | `Sekai Guide Yellow` -> `NOTE_CONNECTION_YELLOW_SEAMLESS`   |
| Red     | `Sekai Guide Red` -> `NOTE_CONNECTION_RED_SEAMLESS`         |
| Purple  | `Sekai Guide Purple` -> `NOTE_CONNECTION_PURPLE_SEAMLESS`   |
| Cyan    | `Sekai Guide Cyan` -> `NOTE_CONNECTION_CYAN_SEAMLESS`       |
| Blue    | `Sekai Guide Blue` -> `NOTE_CONNECTION_BLUE_SEAMLESS`       |
| Neutral | `Sekai Guide Neutral` -> `NOTE_CONNECTION_NEUTRAL_SEAMLESS` |
| Black   | `Sekai Guide Black` -> `NOTE_CONNECTION_NEUTRAL_SEAMLESS`   |

#### Damage Slide Connectors

| Connector        | Precedence                                                                |
|------------------|---------------------------------------------------------------------------|
| Damage           | `Sekai Damage Slide Connection` -> `NOTE_CONNECTION_PURPLE_SEAMLESS`      |
| Damage (Touched) | `Sekai Damage Slide Connection Active` -> `NOTE_CONNECTION_RED_SEAMLESS`  |

#### Color Variants

Missing or incomplete sets use the default sprites for the note or connector.

| Role                  | Sprite | Required Set |
|-----------------------|--------|--------------|
| Note Bodies           | `Sekai {Normal, Slide, Flick, Down Flick, Damage} Note {Left, Middle, Right} <Color>` | All 3 slices |
| Critical Note Bodies  | `Sekai {Critical, Critical Slide, Critical Flick, Critical Down Flick} Note {Left, Middle, Right} <Color>` | All 3 slices |
| Trace Bodies          | `Sekai {Normal Trace, Trace Flick, Trace Down Flick} Note {Left, Middle, Right} <Color>` | All 3 slices |
| Critical Trace Bodies | `Sekai {Critical Trace, Critical Trace Flick, Critical Trace Down Flick} Note {Left, Middle, Right} <Color>` | All 3 slices |
| Slide Tick Diamonds   | `Sekai {Normal, Critical} Slide Diamond <Color>` | Individual |
| Trace Diamonds        | `Sekai {Normal Trace, Trace Flick, Trace Down Flick, Critical Trace, Critical Trace Flick, Critical Trace Down Flick} Diamond <Color>` | Individual |
| Slots & Slot Glows    | `Sekai {Slot, Slot Glow} {Normal, Slide, Flick, Down Flick, Critical, Critical Slide, Critical Flick, Critical Down Flick} <Color>` | Individual |
| Flick Arrows          | `Sekai {Flick Arrow, Critical Flick Arrow} {Up, Up Left, Down, Down Left} {1..6} <Color>` | All 4 directions and 6 widths |
| Active Connectors     | `Sekai {Normal, Critical} Active Slide Connection {Normal, Active} <Color>` | Both states |
| Connector Slot Glows  | `Sekai {Normal, Critical} Slide Slot Glow <Color>` | Individual |
| Damage Connectors     | `Sekai Damage Slide Connection <Color>`, `Sekai Damage Slide Connection Active <Color>` | Both states |

### Effect Clips

| Name                   |
|------------------------|
| `Sekai Tick`           |
| `Sekai Critical Tap`   |
| `Sekai Critical Flick` |
| `Sekai Critical Hold`  |
| `Sekai Critical Tick`  |
| `Sekai Trace`          |
| `Sekai Critical Trace` |

### Particle Effects

| Name                                   |
|----------------------------------------|
| `Sekai Note Lane Linear`               |
| `Sekai Critical Lane Linear`           |
| `Sekai Critical Flick Lane Linear`     |
| `Sekai Slot Linear Tap Cyan`           |
| `Sekai Slot Linear Slide Tap Green`    |
| `Sekai Slot Linear Alternative Red`    |
| `Sekai Slot Linear Tap Yellow`         |
| `Sekai Slot Linear Slide Tap Yellow`   |
| `Sekai Slot Linear Alternative Yellow` |
| `Sekai Trace Note Circular Green`      |
| `Sekai Trace Note Linear Green`        |
| `Sekai Critical Slide Circular Yellow` |
| `Sekai Critical Slide Linear Yellow`   |
| `Sekai Critical Flick Circular Yellow` |
| `Sekai Critical Flick Linear Yellow`   |
| `Sekai Trace Note Circular Yellow`     |
| `Sekai Trace Note Linear Yellow`       |
| `Sekai Normal Slide Trail Linear`      |
| `Sekai Slot Linear Slide Green`        |
| `Sekai Critical Slide Trail Linear`    |
| `Sekai Slot Linear Slide Yellow`       |

#### Color Variants

Each missing colored effect uses its existing default. Trace flicks share the
corresponding flick directional and lane effects.

| Role                | Name |
|---------------------|------|
| Note Hits           | `Sekai {Normal, Slide, Flick, Down Flick} Note {Circular, Linear, Slot Linear} <Color>` |
| Critical Note Hits  | `Sekai {Critical, Critical Slide, Critical Flick, Critical Down Flick} Note {Circular, Linear, Slot Linear} <Color>` |
| Flick Directions    | `Sekai {Flick Note, Down Flick Note, Critical Note, Critical Down Flick Note} Directional <Color>` |
| Lane Effects        | `Sekai {Note, Slide, Flick, Down Flick, Critical, Critical Slide, Critical Flick, Critical Down Flick} Lane Linear <Color>` |
| Trace Hits          | `Sekai {Normal, Critical} Trace Note {Circular, Linear} <Color>` |
| Slide Ticks         | `Sekai {Normal, Critical} Slide Tick Note <Color>` |
| Damage Hits         | `Sekai Damage Note {Circular, Linear} <Color>` |
| Slide Connectors    | `Sekai {Normal, Critical} Slide Connector {Circular, Linear, Trail Linear, Slot Linear} <Color>` |
