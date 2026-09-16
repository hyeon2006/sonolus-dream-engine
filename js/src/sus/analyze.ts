const TICKS_PER_BEAT = 480
const MIN_LANE = 2
const MAX_LANE = 13

export type Direction = 'left' | 'up' | 'right'
export type ConnectorEase = 'in' | 'linear' | 'out'

export type Rgba = {
    red: number
    green: number
    blue: number
    alpha: number
}

export type BpmChange = {
    beat: number
    bpm: number
}

export type TimeScaleChange = {
    beat: number
    timeScale: number
}

export type SingleNote = {
    beat: number
    critical: boolean
    lane: number
    size: number
    direction?: Direction
}

type PositionedPoint = {
    beat: number
    lane: number
    size: number
}

export type SlideConnection = PositionedPoint &
    (
        | { type: 'start'; critical: boolean; ease: ConnectorEase }
        | { type: 'end'; critical: boolean; direction?: Direction }
        | { type: 'tick'; critical: boolean; ease: ConnectorEase }
        | { type: 'attach'; critical: boolean; ease: ConnectorEase }
        | { type: 'anchor'; ease: ConnectorEase }
    )

export type Slide = {
    critical: boolean
    connections: SlideConnection[]
}

export type GuidePoint = PositionedPoint & {
    ease: ConnectorEase
}

export type Guide = {
    color: Rgba
    points: GuidePoint[]
}

export type HolodoriScore = {
    offset: number
    bpmChanges: BpmChange[]
    timeScaleChanges: TimeScaleChange[]
    measureBeats: number[]
    skillBeats: number[]
    singles: SingleNote[]
    slides: Slide[]
    guides: Guide[]
}

type Bar = {
    measure: number
    ticksPerMeasure: number
    ticks: number
}

type RawNote = {
    tick: number
    lane: number
    width: number
    type: number
}

type ParsedCell = {
    position: number
    cell: string
    total: number
}

const charToInt = (character: string): number => {
    const code = character.charCodeAt(0)
    if (code >= 48 && code <= 57) return code - 48
    if (code >= 97 && code <= 122) return code - 87
    if (code >= 65 && code <= 90) return code - 29
    return 0
}

const getBars = (barLengths: [number, number][]): Bar[] => {
    const lengths: [number, number][] = barLengths.length ? barLengths : [[0, 4]]
    const sorted = [...lengths].sort(([a], [b]) => a - b)
    const first = sorted[0]
    if (!first) throw new Error('Unexpected missing bar')

    const bars: Bar[] = [
        {
            measure: first[0],
            ticksPerMeasure: Math.trunc(first[1] * TICKS_PER_BEAT),
            ticks: 0,
        },
    ]
    for (let index = 1; index < sorted.length; index++) {
        const previous = sorted[index - 1]
        const current = sorted[index]
        if (!previous || !current) continue
        bars.push({
            measure: current[0],
            ticksPerMeasure: Math.trunc(current[1] * TICKS_PER_BEAT),
            ticks: Math.trunc((current[0] - previous[0]) * previous[1] * TICKS_PER_BEAT),
        })
    }
    return bars
}

const getTicks = (bars: Bar[], measure: number, position: number, total: number): number => {
    let barIndex = 0
    let accumulatedTicks = 0
    for (const [index, bar] of bars.entries()) {
        if (bar.measure > measure) break
        barIndex = index
        accumulatedTicks += bar.ticks
    }
    const bar = bars[barIndex]
    if (!bar) throw new Error('Unexpected missing bar')
    return (
        accumulatedTicks +
        (measure - bar.measure) * bar.ticksPerMeasure +
        Math.floor((position * bar.ticksPerMeasure) / total)
    )
}

const parseCells = (data: string): ParsedCell[] => {
    const cells: { position: number; cell: string }[] = []
    let index = 0
    let position = 0
    while (index < data.length) {
        if (index + 4 <= data.length && data[index] === '0' && data[index + 1] === 'x') {
            position += charToInt(data[index + 2] ?? '') * 62 + charToInt(data[index + 3] ?? '')
            index += 4
            continue
        }
        if (index + 2 > data.length) break
        const cell = data.slice(index, index + 2)
        if (cell !== '00') cells.push({ position, cell })
        position++
        index += 2
    }
    return position > 0 ? cells.map((cell) => ({ ...cell, total: position })) : []
}

const parseNotes = (
    data: string,
    bars: Bar[],
    measure: number,
    laneCharacter: string,
): RawNote[] => {
    const lane = charToInt(laneCharacter)
    return parseCells(data)
        .filter(({ cell }) => !cell.startsWith('0'))
        .map(({ position, cell, total }) => ({
            tick: getTicks(bars, measure, position, total),
            lane,
            width: charToInt(cell[1] ?? ''),
            type: charToInt(cell[0] ?? ''),
        }))
}

const toBeat = (tick: number): number => Math.round((tick / TICKS_PER_BEAT) * 1e6) / 1e6
const toLane = ({ lane, width }: RawNote): number => lane + width / 2 - 8
const toSize = ({ width }: RawNote): number => width / 2
const noteKey = ({ tick, lane }: RawNote): string => `${tick}-${lane}`

const getEase = (key: string, easeIns: Set<string>, easeOuts: Set<string>): ConnectorEase => {
    if (easeIns.has(key)) return 'in'
    if (easeOuts.has(key)) return 'out'
    return 'linear'
}

const groupGhosts = (stream: RawNote[]): RawNote[][] => {
    const result: RawNote[][] = []
    let current: RawNote[] = []
    for (const note of [...stream].sort((a, b) => a.tick - b.tick)) {
        current.push(note)
        if (note.type !== 2) continue
        result.push(current)
        current = []
    }
    return result
}

const parseRgba = (value: string | undefined): Rgba => {
    const hex = value?.trim().replace(/^["'#]|["']$/g, '') ?? ''
    if (/^[\da-f]{8}$/i.test(hex)) {
        return {
            red: parseInt(hex.slice(0, 2), 16) / 255,
            green: parseInt(hex.slice(2, 4), 16) / 255,
            blue: parseInt(hex.slice(4, 6), 16) / 255,
            alpha: parseInt(hex.slice(6, 8), 16) / 255,
        }
    }
    if (/^[\da-f]{6}$/i.test(hex)) {
        return {
            red: parseInt(hex.slice(0, 2), 16) / 255,
            green: parseInt(hex.slice(2, 4), 16) / 255,
            blue: parseInt(hex.slice(4, 6), 16) / 255,
            alpha: 1,
        }
    }
    if (/^[\da-f]{4}$/i.test(hex)) {
        return {
            red: parseInt(hex[0] ?? '0', 16) / 15,
            green: parseInt(hex[1] ?? '0', 16) / 15,
            blue: parseInt(hex[2] ?? '0', 16) / 15,
            alpha: parseInt(hex[3] ?? 'f', 16) / 15,
        }
    }
    return { red: 0, green: 1, blue: 0, alpha: 1 }
}

export const analyzeHolodoriSus = (sus: string): HolodoriScore => {
    const lines = sus
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line.startsWith('#'))

    const barLengths: [number, number][] = []
    let lastMeasure = 0
    for (const line of lines) {
        const measureMatch = /^#(\d{3})/.exec(line)
        if (measureMatch) lastMeasure = Math.max(lastMeasure, Number(measureMatch[1]))
        const match = /^#(\d{3})02:(.+)$/.exec(line)
        if (!match) continue
        const measure = Number(match[1])
        const length = Number(match[2])
        if (Number.isFinite(measure) && Number.isFinite(length)) barLengths.push([measure, length])
    }
    const bars = getBars(barLengths)

    let waveOffset = 0
    let baseBpm = 120
    const bpmDefinitions = new Map<string, number>()
    const nmsDefinitions = new Map<string, number>()
    const colorDefinitions = new Map<string, string>()
    const bpmChanges: { tick: number; bpm: number }[] = []
    const timeScaleChanges: { tick: number; timeScale: number }[] = []
    const skillTicks = new Set<number>()
    const taps: RawNote[] = []
    const directionals: RawNote[] = []
    const slideStreams = new Map<number, RawNote[]>()
    const ghostStreams = new Map<number, RawNote[]>()
    const ghostColors = new Map<number, string>()

    for (const line of lines) {
        const colon = line.indexOf(':', 1)
        if (colon === -1) {
            const match = /^#(\S+)(?:\s+(.*))?$/.exec(line)
            const key = match?.[1]?.toUpperCase()
            const value = (match?.[2] ?? '').trim().replace(/^"|"$/g, '')
            if (key === 'WAVEOFFSET') waveOffset = Number(value || 0)
            if (key === 'BASEBPM') baseBpm = Number(value || 120)
            if (key === 'SP_SKILL') {
                const skill = /^(\d{3})\s+(\d+)\/(\d+)\s+(\d+)/.exec(value)
                if (skill) {
                    const denominator = Number(skill[3])
                    skillTicks.add(
                        getTicks(
                            bars,
                            Number(skill[1]),
                            denominator ? Number(skill[2]) : 0,
                            denominator || 1,
                        ),
                    )
                }
            }
            continue
        }

        const header = line.slice(1, colon).trim()
        const data = line.slice(colon + 1).trim()

        const ghost = /^(\d{3})9([0-9a-z])([0-9a-zA-Z])([0-9A-Fa-f]{4})$/.exec(header)
        if (ghost) {
            const measure = Number(ghost[1])
            const channel = charToInt(ghost[3] ?? '')
            ghostColors.set(channel, ghost[4] ?? '')
            const stream = ghostStreams.get(channel) ?? []
            stream.push(...parseNotes(data, bars, measure, ghost[2] ?? '0'))
            ghostStreams.set(channel, stream)
            continue
        }

        if (header.startsWith('COLOR') && header.length === 9) {
            colorDefinitions.set(header.slice(5), data)
            continue
        }
        if (header.startsWith('BPM') && header.length === 5) {
            bpmDefinitions.set(header.slice(3), Number(data))
            continue
        }
        if (header.startsWith('NMS') && header.length === 5) {
            nmsDefinitions.set(header.slice(3), Number(data))
            continue
        }
        if (!/^\d{3}..$/.test(header)) continue

        const measure = Number(header.slice(0, 3))
        const event = header[3]
        const laneCharacter = header[4] ?? '0'
        const suffix = header.slice(3)
        if (suffix === '02') continue
        if (suffix === '08') {
            for (const { position, cell, total } of parseCells(data)) {
                bpmChanges.push({
                    tick: getTicks(bars, measure, position, total),
                    bpm: bpmDefinitions.get(cell) ?? baseBpm,
                })
            }
            continue
        }
        if (suffix === '0A') {
            for (const { position, cell, total } of parseCells(data)) {
                timeScaleChanges.push({
                    tick: getTicks(bars, measure, position, total),
                    timeScale: nmsDefinitions.get(cell) ?? 1,
                })
            }
            continue
        }
        if (suffix === '0B') {
            for (const { position, cell, total } of parseCells(data)) {
                const slot = charToInt(cell[0] ?? '') * 62 + charToInt(cell[1] ?? '')
                if (slot >= 1) skillTicks.add(getTicks(bars, measure, position, total))
            }
            continue
        }
        if (event === '1') taps.push(...parseNotes(data, bars, measure, laneCharacter))
        if (event === '5') directionals.push(...parseNotes(data, bars, measure, laneCharacter))
    }

    for (const line of lines) {
        const match = /^#(\d{3})3([0-9a-z])([0-9a-zA-Z]):(.+)$/.exec(line)
        if (!match) continue
        const channel = charToInt(match[3] ?? '')
        const stream = slideStreams.get(channel) ?? []
        stream.push(...parseNotes(match[4] ?? '', bars, Number(match[1]), match[2] ?? '0'))
        slideStreams.set(channel, stream)
    }

    const rawSlides: RawNote[][] = []
    for (const stream of slideStreams.values()) {
        const seen = new Set<string>()
        const sorted = [...stream]
            .sort((a, b) => a.tick - b.tick)
            .filter((note) => {
                const key = `${note.tick}-${note.lane}-${note.type}-${note.width}`
                if (seen.has(key)) return false
                seen.add(key)
                return true
            })
        const starts: RawNote[] = []
        const relays: RawNote[] = []
        for (const note of sorted) {
            if (note.type === 1) {
                starts.push(note)
            } else if (note.type === 2) {
                const startIndex = starts.findIndex((start) => start.tick <= note.tick)
                if (startIndex === -1) continue
                const start = starts.splice(startIndex, 1)[0]
                if (!start) continue
                const matchedRelays = relays.filter(
                    (relay) => relay.tick >= start.tick && relay.tick <= note.tick,
                )
                for (const relay of matchedRelays) relays.splice(relays.indexOf(relay), 1)
                rawSlides.push([start, ...matchedRelays.sort((a, b) => a.tick - b.tick), note])
            } else {
                relays.push(note)
            }
        }
    }

    const criticals = new Set<string>()
    const stepIgnores = new Set<string>()
    const flicks = new Map<string, Direction>()
    const easeIns = new Set<string>()
    const easeOuts = new Set<string>()
    for (const note of directionals) {
        const key = noteKey(note)
        if (note.type === 1) flicks.set(key, 'up')
        if (note.type === 3) flicks.set(key, 'left')
        if (note.type === 4) flicks.set(key, 'right')
        if (note.type === 2) easeIns.add(key)
        if (note.type === 5 || note.type === 6) easeOuts.add(key)
    }
    for (const note of taps) {
        const key = noteKey(note)
        if (note.type === 2 || note.type === 6) criticals.add(key)
        if (note.type === 3) stepIgnores.add(key)
    }

    const slideStarts = new Set(
        rawSlides.flatMap((slide) => {
            const start = slide[0]
            return start ? [noteKey(start)] : []
        }),
    )
    const slideEnds = new Set(
        rawSlides.flatMap((slide) => {
            const end = slide.at(-1)
            return end ? [noteKey(end)] : []
        }),
    )
    const tapKeys = new Set(taps.filter(({ type }) => type === 1).map(noteKey))
    const singles: SingleNote[] = []
    for (const note of taps) {
        if (note.type !== 1 || note.lane < MIN_LANE || note.lane > MAX_LANE) continue
        const key = noteKey(note)
        if (slideStarts.has(key)) continue
        const direction = flicks.get(key)
        singles.push({
            beat: toBeat(note.tick),
            critical: criticals.has(key),
            lane: toLane(note),
            size: toSize(note),
            ...(direction ? { direction } : {}),
        })
    }
    for (const note of directionals) {
        const direction =
            note.type === 1
                ? ('up' as const)
                : note.type === 3
                  ? ('left' as const)
                  : note.type === 4
                    ? ('right' as const)
                    : undefined
        if (!direction || note.lane < MIN_LANE || note.lane > MAX_LANE) continue
        const key = noteKey(note)
        if (slideStarts.has(key) || slideEnds.has(key) || tapKeys.has(key)) continue
        singles.push({
            beat: toBeat(note.tick),
            critical: criticals.has(key),
            lane: toLane(note),
            size: toSize(note),
            direction,
        })
    }
    const emitted = new Set([
        ...taps.filter(({ type }) => type === 1).map(noteKey),
        ...directionals.filter(({ type }) => type === 1 || type === 3 || type === 4).map(noteKey),
        ...rawSlides.flatMap((slide) => slide.map(noteKey)),
    ])
    for (const note of taps) {
        const key = noteKey(note)
        if (note.type !== 2 || note.lane < MIN_LANE || note.lane > MAX_LANE || emitted.has(key))
            continue
        singles.push({
            beat: toBeat(note.tick),
            critical: true,
            lane: toLane(note),
            size: toSize(note),
        })
    }

    const slides: Slide[] = []
    for (const rawSlide of rawSlides) {
        const start = rawSlide[0]
        if (!start || rawSlide.length < 2) continue
        const critical = criticals.has(noteKey(start))
        const connections: SlideConnection[] = []
        for (const [index, note] of rawSlide.entries()) {
            const key = noteKey(note)
            const base = { beat: toBeat(note.tick), lane: toLane(note), size: toSize(note) }
            if (index === 0) {
                connections.push({
                    ...base,
                    type: 'start',
                    critical,
                    ease: getEase(key, easeIns, easeOuts),
                })
            } else if (index === rawSlide.length - 1) {
                const direction = flicks.get(key)
                connections.push({
                    ...base,
                    type: 'end',
                    critical: critical || criticals.has(key),
                    ...(direction ? { direction } : {}),
                })
            } else if (note.type === 3) {
                connections.push({
                    ...base,
                    type: stepIgnores.has(key) ? 'attach' : 'tick',
                    critical,
                    ease: getEase(key, easeIns, easeOuts),
                })
            } else if (note.type !== 4) {
                connections.push({
                    ...base,
                    type: 'anchor',
                    ease: getEase(key, easeIns, easeOuts),
                })
            }
        }
        if (connections.length >= 2) slides.push({ critical, connections })
    }

    const guides: Guide[] = []
    for (const [channel, stream] of ghostStreams) {
        const colorId = ghostColors.get(channel)
        const color = parseRgba(colorDefinitions.get(colorId ?? '') ?? colorId)
        for (const rawGuide of groupGhosts(stream)) {
            if (rawGuide.length < 2) continue
            guides.push({
                color,
                points: rawGuide.map((note) => ({
                    beat: toBeat(note.tick),
                    lane: toLane(note),
                    size: toSize(note),
                    ease: getEase(noteKey(note), easeIns, easeOuts),
                })),
            })
        }
    }

    const normalizedBpms = bpmChanges.length ? bpmChanges : [{ tick: 0, bpm: 120 }]
    const normalizedTimeScales = timeScaleChanges.length
        ? [
              ...timeScaleChanges,
              ...(timeScaleChanges.some(({ tick }) => tick === 0)
                  ? []
                  : [{ tick: 0, timeScale: 1 }]),
          ]
        : [{ tick: 0, timeScale: 1 }]

    return {
        offset: -waveOffset,
        bpmChanges: normalizedBpms
            .sort((a, b) => a.tick - b.tick)
            .map(({ tick, bpm }) => ({ beat: toBeat(tick), bpm })),
        timeScaleChanges: normalizedTimeScales
            .sort((a, b) => a.tick - b.tick)
            .map(({ tick, timeScale }) => ({ beat: toBeat(tick), timeScale })),
        measureBeats: Array.from({ length: lastMeasure + 1 }, (_, measure) =>
            toBeat(getTicks(bars, measure, 0, 1)),
        ),
        skillBeats: [...skillTicks].sort((a, b) => a - b).map(toBeat),
        singles: singles.sort((a, b) => a.beat - b.beat || a.lane - b.lane),
        slides,
        guides,
    }
}
