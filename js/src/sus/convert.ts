import {
    EngineArchetypeDataName,
    EngineArchetypeName,
    LevelData,
    LevelDataEntity,
} from '@sonolus/core'
import { ConnectorEase, Guide, Rgba, SlideConnection, analyzeHolodoriSus } from './analyze.js'

const CONNECTOR_EASES: Record<ConnectorEase, number> = {
    linear: 1,
    in: 2,
    out: 3,
}

const GUIDE_GHOST = 100
const ACTIVE_NORMAL = 1
const ACTIVE_CRITICAL = 2
const EPSILON = 1e-6

type SimLineCandidate = {
    beat: number
    lane: number
    entity: LevelDataEntity
}

export const susToLevelData = (sus: string, offset = 0): LevelData => {
    const score = analyzeHolodoriSus(sus)
    let nextId = 0
    const getRef = (entity: LevelDataEntity): string => (entity.name ??= (nextId++).toString(16))
    const entities: LevelDataEntity[] = [{ archetype: 'Initialization', data: [] }]
    const simLineCandidates: SimLineCandidate[] = []

    const timeScaleGroup = createEntity('#TIMESCALE_GROUP')
    entities.push(timeScaleGroup)

    for (const change of score.bpmChanges) {
        const entity = createEntity(EngineArchetypeName.BpmChange)
        addValue(entity, EngineArchetypeDataName.Beat, change.beat)
        addValue(entity, EngineArchetypeDataName.Bpm, change.bpm)
        entities.push(entity)
    }

    let previousTimeScaleChange: LevelDataEntity | undefined
    for (const change of score.timeScaleChanges) {
        const entity = createEntity(EngineArchetypeName.TimeScaleChange)
        addValue(entity, EngineArchetypeDataName.Beat, change.beat)
        addValue(entity, EngineArchetypeDataName.TimeScale, change.timeScale)
        addValue(entity, '#TIMESCALE_SKIP', 0)
        addRef(entity, '#TIMESCALE_GROUP', getRef(timeScaleGroup))
        addValue(entity, '#TIMESCALE_EASE', 0)
        addValue(entity, 'hideNotes', 0)
        if (previousTimeScaleChange) {
            addRef(previousTimeScaleChange, 'next', getRef(entity))
        } else {
            addRef(timeScaleGroup, 'first', getRef(entity))
        }
        previousTimeScaleChange = entity
        entities.push(entity)
    }

    for (const beat of score.skillBeats) {
        const entity = createEntity('SkillActivationLine')
        addValue(entity, EngineArchetypeDataName.Beat, beat)
        addRef(entity, '#TIMESCALE_GROUP', getRef(timeScaleGroup))
        entities.push(entity)
    }

    for (const beat of score.measureBeats) {
        const entity = createEntity('MeasureLine')
        addValue(entity, EngineArchetypeDataName.Beat, beat)
        addRef(entity, '#TIMESCALE_GROUP', getRef(timeScaleGroup))
        entities.push(entity)
    }

    for (const note of score.singles) {
        const entity = createNoteEntity(
            (note.critical ? 'Critical' : 'Normal') +
                (note.direction ? 'TraceFlickNote' : 'TapNote'),
            note.beat,
            note.lane,
            note.size,
            timeScaleGroup,
            getRef,
        )
        addValue(entity, 'direction', 0)
        addValue(entity, 'isAttached', 0)
        addValue(entity, 'connectorEase', 1)
        addSegment(
            entity,
            note.critical ? ACTIVE_CRITICAL : ACTIVE_NORMAL,
            activeRgba(note.critical),
        )
        entities.push(entity)
        simLineCandidates.push({ beat: note.beat, lane: note.lane, entity })
    }

    for (const slide of score.slides) {
        const connections = [...slide.connections].sort((a, b) => a.beat - b.beat)
        const firstConnection = connections[0]
        if (!firstConnection) continue

        let head: LevelDataEntity | undefined
        let previousJoint: LevelDataEntity | undefined
        let previousNote: LevelDataEntity | undefined
        let nextHiddenTickBeat = Math.floor(firstConnection.beat * 2 + 1) / 2
        const queuedAttaches: LevelDataEntity[] = []
        const connectors: LevelDataEntity[] = []
        const color = activeRgba(slide.critical)

        for (const connection of connections) {
            const entity = createNoteEntity(
                getSlideArchetype(connection),
                connection.beat,
                connection.lane,
                connection.size,
                timeScaleGroup,
                getRef,
            )
            addValue(entity, 'direction', 0)
            addValue(entity, 'isAttached', connection.type === 'attach' ? 1 : 0)
            addValue(
                entity,
                'connectorEase',
                connection.type === 'end' ? 1 : CONNECTOR_EASES[connection.ease],
            )
            addSegment(entity, slide.critical ? ACTIVE_CRITICAL : ACTIVE_NORMAL, color)
            entities.push(entity)

            head ??= entity
            addRef(entity, 'activeHead', getRef(head))

            if (connection.type === 'start' || connection.type === 'end') {
                simLineCandidates.push({
                    beat: connection.beat,
                    lane: connection.lane,
                    entity,
                })
            }

            if (connection.type === 'attach') {
                queuedAttaches.push(entity)
            } else {
                if (previousJoint) {
                    for (const attach of queuedAttaches) {
                        addRef(attach, 'attachHead', getRef(previousJoint))
                        addRef(attach, 'attachTail', getRef(entity))
                    }
                    queuedAttaches.length = 0

                    while (nextHiddenTickBeat + EPSILON < connection.beat) {
                        if (Math.abs(nextHiddenTickBeat - firstConnection.beat) > EPSILON) {
                            const hiddenTick = createNoteEntity(
                                'TransientHiddenTickNote',
                                roundBeat(nextHiddenTickBeat),
                                connection.lane,
                                connection.size,
                                timeScaleGroup,
                                getRef,
                            )
                            addValue(hiddenTick, 'direction', 0)
                            addValue(hiddenTick, 'isAttached', 1)
                            addValue(hiddenTick, 'connectorEase', 1)
                            addSegment(hiddenTick, ACTIVE_NORMAL, {
                                red: 1,
                                green: 1,
                                blue: 1,
                                alpha: 0,
                            })
                            addRef(hiddenTick, 'activeHead', getRef(head))
                            addRef(hiddenTick, 'attachHead', getRef(previousJoint))
                            addRef(hiddenTick, 'attachTail', getRef(entity))
                            entities.push(hiddenTick)
                        }
                        nextHiddenTickBeat += 0.5
                    }

                    const connector = createEntity('Connector')
                    addRef(connector, 'head', getRef(previousJoint))
                    addRef(connector, 'tail', getRef(entity))
                    entities.push(connector)
                    connectors.push(connector)
                }
                previousJoint = entity
            }

            if (previousNote) addRef(previousNote, 'next', getRef(entity))
            previousNote = entity
        }

        if (queuedAttaches.length) throw new Error('Unexpected slide ending with an attached point')
        if (!head || !previousJoint) throw new Error('Unexpected incomplete slide')
        for (const connector of connectors) {
            addRef(connector, 'segmentHead', getRef(head))
            addRef(connector, 'segmentTail', getRef(previousJoint))
            addRef(connector, 'activeHead', getRef(head))
            addRef(connector, 'activeTail', getRef(previousJoint))
        }
    }

    for (const guide of score.guides) addGuide(guide, entities, timeScaleGroup, getRef)

    addSimLines(simLineCandidates, entities, getRef)

    return {
        bgmOffset: score.offset + offset,
        entities,
    }
}

const createEntity = (archetype: string): LevelDataEntity => ({ archetype, data: [] })

const addValue = (entity: LevelDataEntity, name: string, value: number): void => {
    entity.data.push({ name, value })
}

const addRef = (entity: LevelDataEntity, name: string, ref: string): void => {
    entity.data.push({ name, ref })
}

const createNoteEntity = (
    archetype: string,
    beat: number,
    lane: number,
    size: number,
    timeScaleGroup: LevelDataEntity,
    getRef: (entity: LevelDataEntity) => string,
): LevelDataEntity => {
    const entity = createEntity(archetype)
    addValue(entity, EngineArchetypeDataName.Beat, beat)
    addRef(entity, '#TIMESCALE_GROUP', getRef(timeScaleGroup))
    addValue(entity, 'lane', lane)
    addValue(entity, 'size', size)
    return entity
}

const addSegment = (entity: LevelDataEntity, kind: number, color: Rgba): void => {
    addValue(entity, 'segmentKind', kind)
    addValue(entity, 'segmentRed', color.red)
    addValue(entity, 'segmentGreen', color.green)
    addValue(entity, 'segmentBlue', color.blue)
    addValue(entity, 'segmentAlpha', color.alpha)
}

const activeRgba = (critical: boolean): Rgba =>
    critical ? { red: 1, green: 1, blue: 0, alpha: 1 } : { red: 1, green: 1, blue: 1, alpha: 1 }

const getSlideArchetype = (connection: SlideConnection): string => {
    switch (connection.type) {
        case 'start':
            return `${connection.critical ? 'Critical' : 'Normal'}HeadTapNote`
        case 'end':
            return `${connection.critical ? 'Critical' : 'Normal'}Tail${
                connection.direction ? 'Flick' : 'Trace'
            }Note`
        case 'tick':
        case 'attach':
            return `${connection.critical ? 'Critical' : 'Normal'}TickNote`
        case 'anchor':
            return 'AnchorNote'
    }
}

const addGuide = (
    guide: Guide,
    entities: LevelDataEntity[],
    timeScaleGroup: LevelDataEntity,
    getRef: (entity: LevelDataEntity) => string,
): void => {
    const points = [...guide.points].sort((a, b) => a.beat - b.beat)
    let head: LevelDataEntity | undefined
    let previous: LevelDataEntity | undefined
    const connectors: LevelDataEntity[] = []

    for (const point of points) {
        const entity = createNoteEntity(
            'AnchorNote',
            point.beat,
            point.lane,
            point.size,
            timeScaleGroup,
            getRef,
        )
        addValue(entity, 'direction', 0)
        addValue(entity, 'isAttached', 0)
        addValue(entity, 'connectorEase', CONNECTOR_EASES[point.ease])
        addSegment(entity, GUIDE_GHOST, guide.color)
        entities.push(entity)

        head ??= entity
        if (previous) {
            const connector = createEntity('Connector')
            addRef(connector, 'head', getRef(previous))
            addRef(connector, 'tail', getRef(entity))
            entities.push(connector)
            connectors.push(connector)
            addRef(previous, 'next', getRef(entity))
        }
        previous = entity
    }

    if (!head || !previous) return
    for (const connector of connectors) {
        addRef(connector, 'segmentHead', getRef(head))
        addRef(connector, 'segmentTail', getRef(previous))
    }
}

const addSimLines = (
    candidates: SimLineCandidate[],
    entities: LevelDataEntity[],
    getRef: (entity: LevelDataEntity) => string,
): void => {
    const sorted = [...candidates].sort((a, b) => a.beat - b.beat || a.lane - b.lane)
    const groups: SimLineCandidate[][] = []
    for (const candidate of sorted) {
        const group = groups.at(-1)
        if (!group || Math.abs(candidate.beat - (group[0]?.beat ?? 0)) >= 1e-2) {
            groups.push([candidate])
        } else {
            group.push(candidate)
        }
    }

    for (const group of groups) {
        group.sort((a, b) => a.lane - b.lane)
        for (let index = 1; index < group.length; index++) {
            const left = group[index - 1]
            const right = group[index]
            if (!left || !right) continue
            const simLine = createEntity('SimLine')
            addRef(simLine, 'left', getRef(left.entity))
            addRef(simLine, 'right', getRef(right.entity))
            entities.push(simLine)
        }
    }
}

const roundBeat = (beat: number): number => Math.round(beat * 1e9) / 1e9
