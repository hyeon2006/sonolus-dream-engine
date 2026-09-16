# Next SEKAI Sonolus Engine

A new Project Sekai inspired engine for [Sonolus](https://sonolus.com).

## Installation

```
npm install @next-sekai/sonolus-next-sekai-engine
```

## Documentation

### `version`

Package version.

### `databaseEngineItem`

Partial database engine item compatible with [sonolus-express](https://github.com/Sonolus/sonolus-express).

### `susToLevelData(sus, offset?)`

Converts a Holodori SUS chart directly to Next SEKAI Level Data.

- `sus`: sus chart.
- `offset`: offset (default: `0`).

### Assets

The following assets are exposed as package entry points:

- `EngineConfiguration`
- `EnginePlayData`
- `EngineWatchData`
- `EnginePreviewData`
- `EngineTutorialData`
- `EngineRom`
- `EngineThumbnail`

In Node.js, you can obtain path to assets `import.meta.resolve('sonolus-pjsekai-engine/EngineConfiguration')`.
