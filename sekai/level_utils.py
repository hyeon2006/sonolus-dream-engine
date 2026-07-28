from __future__ import annotations

import itertools
import math
import struct
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

from sonolus.build.collection import Asset
from sonolus.script.archetype import PlayArchetype
from sonolus.script.level import Level, LevelData
from sonolus.script.timing import TimescaleEase

from sekai.lib.connector import ConnectorKind, is_guide_connector
from sekai.lib.ease import EaseType
from sekai.lib.layout import FlickDirection
from sekai.lib.level_config import EngineRevision
from sekai.lib.note import NoteKind
from sekai.play.bpm_change import BpmChange
from sekai.play.connector import Connector
from sekai.play.initialization import Initialization
from sekai.play.note import NOTE_ARCHETYPES, BaseNote
from sekai.play.sim_line import SimLine
from sekai.play.timescale import TimescaleChange, TimescaleGroup


def _build_note_archetype_lookup() -> dict[tuple[NoteKind, bool], type[PlayArchetype]]:
    lookup: dict[tuple[NoteKind, bool], type[PlayArchetype]] = {}
    for archetype in NOTE_ARCHETYPES:
        is_fake = str(archetype.name).startswith("Fake")
        lookup[(cast(NoteKind, archetype.key), is_fake)] = archetype
    return lookup


_NOTE_ARCHETYPE_BY_KIND = _build_note_archetype_lookup()

_SIM_LINE_EXCLUDED_KINDS = frozenset(
    {NoteKind.ANCHOR, NoteKind.NORM_TICK, NoteKind.CRIT_TICK, NoteKind.HIDE_TICK, NoteKind.HIDE_DAMAGE_TICK}
)

_ACTIVE_HOLD_SEGMENT_KINDS = frozenset(
    {
        ConnectorKind.ACTIVE_NORMAL,
        ConnectorKind.ACTIVE_CRITICAL,
        ConnectorKind.ACTIVE_FAKE_NORMAL,
        ConnectorKind.ACTIVE_FAKE_CRITICAL,
    }
)

# Segment kinds whose connectors track touches through their section's active head/tail refs.
_INPUT_TRACKED_SEGMENT_KINDS = _ACTIVE_HOLD_SEGMENT_KINDS | {ConnectorKind.DAMAGE}

_DAMAGE_TICK_STEP = 0.5
_BEAT_EPSILON = 1e-6


def _build_silent_wav(duration_seconds: float = 60.0, sample_rate: int = 8000) -> bytes:
    num_samples = int(duration_seconds * sample_rate)
    data_size = num_samples  # 1 channel, 8-bit
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        1,  # channels
        sample_rate,
        sample_rate,  # byte rate = sample_rate * channels * bits/8
        1,  # block align
        8,  # bits per sample
        b"data",
        data_size,
    )
    return header + b"\x80" * data_size


@dataclass
class LevelBpmChange:
    beat: float
    bpm: float


@dataclass
class LevelTimescaleChange:
    beat: float
    timescale: float
    timescale_skip: float = 0.0
    timescale_ease: TimescaleEase = TimescaleEase.NONE
    hide_notes: bool = False


@dataclass
class LevelTimescaleGroup:
    changes: list[LevelTimescaleChange] = field(default_factory=list)
    force_note_speed: float = 0.0


@dataclass
class LevelNote:
    beat: float
    lane: float
    size: float
    kind: NoteKind
    timescale_group: LevelTimescaleGroup | None = None
    direction: FlickDirection = FlickDirection.UP_OMNI
    is_fake: bool = False
    segment_kind: ConnectorKind = ConnectorKind.NONE
    segment_red: float = -1.0
    segment_green: float = -1.0
    segment_blue: float = -1.0
    segment_alpha: float = 1.0
    connector_ease: EaseType = EaseType.LINEAR
    attach: LevelSlide | None = None


@dataclass
class LevelSlide:
    notes: list[LevelNote] = field(default_factory=list)


type LevelEntities = LevelBpmChange | LevelTimescaleGroup | LevelNote | LevelSlide


def _note_archetype_for(kind: NoteKind, is_fake: bool) -> type[PlayArchetype]:
    key = (kind, is_fake)
    if key not in _NOTE_ARCHETYPE_BY_KIND and is_fake:
        key = (kind, False)
    return _NOTE_ARCHETYPE_BY_KIND[key]


def build_level(
    name: str,
    title: str,
    bgm: Asset | None,
    entities: list[LevelEntities],
) -> Level:
    bpm_changes: list[LevelBpmChange] = []
    level_ts_groups: list[LevelTimescaleGroup] = []
    top_notes: list[LevelNote] = []
    slides: list[LevelSlide] = []

    for entity in entities:
        if isinstance(entity, LevelBpmChange):
            bpm_changes.append(entity)
        elif isinstance(entity, LevelTimescaleGroup):
            level_ts_groups.append(entity)
        elif isinstance(entity, LevelNote):
            top_notes.append(entity)
        elif isinstance(entity, LevelSlide):
            slides.append(entity)
        else:
            raise TypeError(f"Unsupported level entity: {type(entity).__name__}")

    out_entities: list[PlayArchetype] = []

    default_ts_group: TimescaleGroup | None = None
    ts_group_map: dict[int, TimescaleGroup] = {}
    for level_group in level_ts_groups:
        group, group_entities = _build_timescale_group(level_group)
        ts_group_map[id(level_group)] = group
        out_entities.extend(group_entities)

    def resolve_ts_group(level_group: LevelTimescaleGroup | None) -> TimescaleGroup:
        nonlocal default_ts_group
        if level_group is not None:
            return ts_group_map[id(level_group)]
        if default_ts_group is None:
            default_level_group = LevelTimescaleGroup(changes=[LevelTimescaleChange(beat=0.0, timescale=1.0)])
            default_ts_group, group_entities = _build_timescale_group(default_level_group)
            out_entities.extend(group_entities)
        return default_ts_group

    note_entities: list[BaseNote] = []
    slide_non_attached: dict[int, list[BaseNote]] = {}

    def emit_note(level_note: LevelNote) -> BaseNote:
        ts_group = resolve_ts_group(level_note.timescale_group)
        archetype_cls = _note_archetype_for(level_note.kind, level_note.is_fake)
        kwargs: dict[str, object] = {
            "beat": level_note.beat,
            "lane": level_note.lane,
            "size": level_note.size,
            "direction": level_note.direction,
            "connector_ease": level_note.connector_ease,
            "segment_kind": level_note.segment_kind,
            "segment_red": level_note.segment_red,
            "segment_green": level_note.segment_green,
            "segment_blue": level_note.segment_blue,
            "segment_alpha": level_note.segment_alpha,
            "timescale_group": ts_group.ref(),
        }
        note = cast(BaseNote, archetype_cls(**kwargs))
        note_entities.append(note)
        out_entities.append(note)
        return note

    pending_attachments: list[tuple[BaseNote, LevelSlide]] = []

    for level_note in top_notes:
        note = emit_note(level_note)
        if level_note.attach is not None:
            pending_attachments.append((note, level_note.attach))

    for slide in slides:
        if len(slide.notes) < 2:
            raise ValueError("LevelSlide must contain at least two notes")
        last_index = len(slide.notes) - 1
        built: list[BaseNote] = []
        non_attached: list[BaseNote] = []
        for ln in slide.notes:
            note = emit_note(ln)
            built.append(note)
            if ln.attach is None:
                non_attached.append(note)
            else:
                pending_attachments.append((note, ln.attach))

        for prev_note, next_note in itertools.pairwise(non_attached):
            prev_note.next_ref = next_note.ref()
        slide_non_attached[id(slide)] = non_attached

        boundary_indices = [i for i, ln in enumerate(slide.notes) if i in (0, last_index) or ln.attach is None]
        segment_kinds = {slide.notes[head].segment_kind for head, _ in itertools.pairwise(boundary_indices)}
        if len(segment_kinds) > 1:
            raise ValueError("A slide must use one segment kind throughout")
        slide_kind = next(iter(segment_kinds))

        for a, b in itertools.pairwise(boundary_indices):
            if slide_kind == ConnectorKind.NONE:
                continue
            if is_guide_connector(slide_kind):
                segment_head = built[a]
                segment_tail = built[b]
            else:
                segment_head = built[0]
                segment_tail = built[last_index]
            connector = Connector(
                head_ref=built[a].ref(),
                tail_ref=built[b].ref(),
                segment_head_ref=segment_head.ref(),
                segment_tail_ref=segment_tail.ref(),
            )
            if slide_kind in _INPUT_TRACKED_SEGMENT_KINDS:
                connector.active_head_ref = built[0].ref()
                connector.active_tail_ref = built[last_index].ref()
            out_entities.append(connector)

        _emit_damage_ticks(slide, built, non_attached, slide_kind, emit_note)

    for note, slide in pending_attachments:
        candidates = slide_non_attached[id(slide)]
        attach_head: BaseNote | None = None
        attach_tail: BaseNote | None = None
        for cand in candidates:
            if cand.beat <= note.beat and (attach_head is None or cand.beat > attach_head.beat):
                attach_head = cand
            if cand.beat >= note.beat and (attach_tail is None or cand.beat < attach_tail.beat):
                attach_tail = cand
        if attach_head is None or attach_tail is None:
            raise ValueError(f"Attached note at beat {note.beat} is outside the non-attached span of its slide")
        note.attach_head_ref = attach_head.ref()
        note.attach_tail_ref = attach_tail.ref()
        note.is_attached = True

    out_entities.extend(BpmChange(beat=level_bpm.beat, bpm=level_bpm.bpm) for level_bpm in bpm_changes)

    _emit_sim_lines(note_entities, out_entities)

    initialization = Initialization(
        revision=EngineRevision.LATEST,
        initial_life=1000,
    )
    out_entities.insert(0, initialization)

    sorted_entities = sorted(
        out_entities,
        key=lambda e: (not isinstance(e, Initialization), getattr(e, "beat", -1.0)),
    )

    return Level(
        name=name,
        title=title,
        bgm=bgm if bgm is not None else _build_silent_wav(),
        data=LevelData(
            bgm_offset=0.0,
            entities=list(sorted_entities),
        ),
    )


def _emit_damage_ticks(
    slide: LevelSlide,
    built: list[BaseNote],
    non_attached: list[BaseNote],
    slide_kind: ConnectorKind,
    emit_note: Callable[..., BaseNote],
) -> None:
    """Emit a TransientHiddenDamageTickNote every half beat over a DAMAGE slide."""
    if slide_kind != ConnectorKind.DAMAGE:
        return
    head_ln = slide.notes[0]
    head_beat = head_ln.beat
    tail_beat = slide.notes[-1].beat

    def emit_tick(beat: float) -> None:
        tick = emit_note(
            LevelNote(
                beat=beat,
                lane=0.0,
                size=0.0,
                kind=NoteKind.HIDE_DAMAGE_TICK,
                timescale_group=head_ln.timescale_group,
                is_fake=head_ln.is_fake,
            )
        )
        attach_head, attach_tail = _bracketing_non_attached(non_attached, beat)
        tick.attach_head_ref = attach_head.ref()
        tick.attach_tail_ref = attach_tail.ref()
        tick.is_attached = True
        tick.active_head_ref = built[0].ref()

    first_step = math.ceil(head_beat / _DAMAGE_TICK_STEP - _BEAT_EPSILON)
    last_step = math.floor(tail_beat / _DAMAGE_TICK_STEP + _BEAT_EPSILON)
    for step in range(first_step, last_step + 1):
        beat = step * _DAMAGE_TICK_STEP
        if abs(beat - head_beat) < _BEAT_EPSILON:
            continue
        emit_tick(beat)
    if tail_beat > last_step * _DAMAGE_TICK_STEP + _BEAT_EPSILON:
        emit_tick(tail_beat)


def _bracketing_non_attached(non_attached: list[BaseNote], beat: float) -> tuple[BaseNote, BaseNote]:
    """Find the consecutive non-attached joints enclosing the beat, attaching backward only at the slide's end."""
    attach_tail: BaseNote | None = None
    for cand in non_attached:
        if cand.beat > beat + _BEAT_EPSILON:
            attach_tail = cand
            break
    if attach_tail is None:
        attach_tail = non_attached[-1]
    attach_head = non_attached[0]
    for cand in non_attached:
        if cand is attach_tail:
            break
        if cand.beat <= beat + _BEAT_EPSILON:
            attach_head = cand
    return attach_head, attach_tail


def _build_timescale_group(
    level_group: LevelTimescaleGroup,
) -> tuple[TimescaleGroup, list[PlayArchetype]]:
    if not level_group.changes:
        raise ValueError("LevelTimescaleGroup must have at least one change")
    group = TimescaleGroup(force_note_speed=level_group.force_note_speed)
    change_entities: list[TimescaleChange] = []
    for level_change in sorted(level_group.changes, key=lambda c: c.beat):
        change = TimescaleChange(
            beat=level_change.beat,
            timescale=level_change.timescale,
            timescale_skip=level_change.timescale_skip,
            timescale_group=group.ref(),
            timescale_ease=level_change.timescale_ease,
            hide_notes=level_change.hide_notes,
        )
        if change_entities:
            change_entities[-1].next_ref = change.ref()
        change_entities.append(change)
    group.first_ref = change_entities[0].ref()
    return group, [group, *change_entities]


def _emit_sim_lines(note_entities: list[BaseNote], out_entities: list[PlayArchetype]) -> None:
    buckets: dict[float, list[BaseNote]] = {}
    for note in note_entities:
        if note.key in _SIM_LINE_EXCLUDED_KINDS:
            continue
        buckets.setdefault(note.beat, []).append(note)
    for group in buckets.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda n: n.lane)
        for left, right in itertools.pairwise(group):
            out_entities.append(SimLine(left_ref=left.ref(), right_ref=right.ref()))
