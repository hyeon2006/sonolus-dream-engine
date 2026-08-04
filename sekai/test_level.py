from sekai.level_utils import LevelBpmChange, LevelNote, LevelSlide, build_level
from sekai.lib.connector import ConnectorKind
from sekai.lib.ease import EaseType
from sekai.lib.note import NoteKind

tap_notes = [
    LevelNote(beat=1.0, lane=-3.0, size=0.5, kind=NoteKind.NORM_TAP),
    LevelNote(beat=1.0, lane=3.0, size=0.5, kind=NoteKind.CRIT_TAP),
    LevelNote(beat=2.0, lane=-3.0, size=0.75, kind=NoteKind.NORM_TAP),
    LevelNote(beat=2.0, lane=3.0, size=0.75, kind=NoteKind.CRIT_TAP),
    LevelNote(beat=3.0, lane=-3.0, size=1.0, kind=NoteKind.NORM_TAP),
    LevelNote(beat=3.0, lane=3.0, size=1.0, kind=NoteKind.CRIT_TAP),
    LevelNote(beat=4.0, lane=-3.0, size=1.5, kind=NoteKind.NORM_TAP),
    LevelNote(beat=4.0, lane=3.0, size=1.5, kind=NoteKind.CRIT_TAP),
    LevelNote(beat=5.0, lane=-3.0, size=2.0, kind=NoteKind.NORM_TAP),
    LevelNote(beat=5.0, lane=3.0, size=2.0, kind=NoteKind.CRIT_TAP),
    LevelNote(beat=5.5, lane=-3.0, size=1.0, kind=NoteKind.NORM_TAP),
    LevelNote(beat=5.5, lane=3.0, size=1.0, kind=NoteKind.CRIT_TAP),
]

flick_notes = [
    LevelNote(beat=6.0, lane=-3.0, size=0.5, kind=NoteKind.NORM_TAIL_FLICK),
    LevelNote(beat=6.0, lane=3.0, size=0.5, kind=NoteKind.CRIT_TAIL_FLICK),
    LevelNote(beat=7.0, lane=-3.0, size=0.75, kind=NoteKind.NORM_TAIL_FLICK),
    LevelNote(beat=7.0, lane=3.0, size=0.75, kind=NoteKind.CRIT_TAIL_FLICK),
    LevelNote(beat=8.0, lane=-3.0, size=1.0, kind=NoteKind.NORM_TAIL_FLICK),
    LevelNote(beat=8.0, lane=3.0, size=1.0, kind=NoteKind.CRIT_TAIL_FLICK),
    LevelNote(beat=9.0, lane=-3.0, size=1.5, kind=NoteKind.NORM_TAIL_FLICK),
    LevelNote(beat=9.0, lane=3.0, size=1.5, kind=NoteKind.CRIT_TAIL_FLICK),
    LevelNote(beat=10.0, lane=-3.0, size=2.0, kind=NoteKind.NORM_TAIL_FLICK),
    LevelNote(beat=10.0, lane=3.0, size=2.0, kind=NoteKind.CRIT_TAIL_FLICK),
]

normal_tail_trace_slide = LevelSlide(
    notes=[
        LevelNote(
            beat=12.0,
            lane=-4.0,
            size=0.75,
            kind=NoteKind.NORM_HEAD_TAP,
            segment_kind=ConnectorKind.ACTIVE_NORMAL,
        ),
        LevelNote(
            beat=14.0,
            lane=0.0,
            size=1.0,
            kind=NoteKind.NORM_TICK,
            segment_kind=ConnectorKind.ACTIVE_NORMAL,
            connector_ease=EaseType.OUT_QUAD,
        ),
        LevelNote(
            beat=16.0,
            lane=-3.0,
            size=1.5,
            kind=NoteKind.NORM_TAIL_TRACE,
        ),
    ]
)

critical_tail_trace_slide = LevelSlide(
    notes=[
        LevelNote(
            beat=12.0,
            lane=4.0,
            size=0.75,
            kind=NoteKind.CRIT_HEAD_TAP,
            segment_kind=ConnectorKind.ACTIVE_CRITICAL,
        ),
        LevelNote(
            beat=14.0,
            lane=0.0,
            size=1.0,
            kind=NoteKind.CRIT_TICK,
            segment_kind=ConnectorKind.ACTIVE_CRITICAL,
            connector_ease=EaseType.IN_QUAD,
        ),
        LevelNote(
            beat=16.0,
            lane=3.0,
            size=1.5,
            kind=NoteKind.CRIT_TAIL_TRACE,
        ),
    ]
)

normal_flick_end_slide = LevelSlide(
    notes=[
        LevelNote(
            beat=18.0,
            lane=-4.0,
            size=0.75,
            kind=NoteKind.NORM_HEAD_TAP,
            segment_kind=ConnectorKind.ACTIVE_NORMAL,
        ),
        LevelNote(
            beat=20.0,
            lane=-1.0,
            size=1.0,
            kind=NoteKind.NORM_TICK,
            segment_kind=ConnectorKind.ACTIVE_NORMAL,
            connector_ease=EaseType.IN_OUT_QUAD,
        ),
        LevelNote(
            beat=22.0,
            lane=-3.0,
            size=1.5,
            kind=NoteKind.NORM_TAIL_FLICK,
        ),
    ]
)

critical_flick_end_slide = LevelSlide(
    notes=[
        LevelNote(
            beat=18.0,
            lane=4.0,
            size=0.75,
            kind=NoteKind.CRIT_HEAD_TAP,
            segment_kind=ConnectorKind.ACTIVE_CRITICAL,
        ),
        LevelNote(
            beat=20.0,
            lane=1.0,
            size=1.0,
            kind=NoteKind.CRIT_TICK,
            segment_kind=ConnectorKind.ACTIVE_CRITICAL,
            connector_ease=EaseType.OUT_IN_QUAD,
        ),
        LevelNote(
            beat=22.0,
            lane=3.0,
            size=1.5,
            kind=NoteKind.CRIT_TAIL_FLICK,
        ),
    ]
)

guide = LevelSlide(
    notes=[
        LevelNote(
            beat=24.0,
            lane=-2.0,
            size=1.0,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=1.0,
            segment_green=0.0,
            segment_blue=0.0,
        ),
        LevelNote(
            beat=25.0,
            lane=0.0,
            size=1.5,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=0.0,
            segment_green=1.0,
            segment_blue=0.0,
            segment_alpha=0.5,
        ),
        LevelNote(
            beat=26.0,
            lane=2.0,
            size=1.0,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=0.0,
            segment_green=0.0,
            segment_blue=1.0,
        ),
    ]
)

short_red_to_cyan_guide = LevelSlide(
    notes=[
        LevelNote(
            beat=28.0,
            lane=-5.0,
            size=0.75,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=1.0,
            segment_green=0.0,
            segment_blue=0.0,
            segment_alpha=1.0,
        ),
        LevelNote(
            beat=28.25,
            lane=-3.0,
            size=0.75,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=0.0,
            segment_green=1.0,
            segment_blue=1.0,
            segment_alpha=1.0,
        ),
    ]
)

short_magenta_to_green_fade_guide = LevelSlide(
    notes=[
        LevelNote(
            beat=29.0,
            lane=3.0,
            size=1.5,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=1.0,
            segment_green=0.0,
            segment_blue=1.0,
            segment_alpha=1.0,
            connector_ease=EaseType.OUT_IN_QUAD,
        ),
        LevelNote(
            beat=29.5,
            lane=5.0,
            size=0.5,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=0.0,
            segment_green=1.0,
            segment_blue=0.0,
            segment_alpha=0.0,
        ),
    ]
)

long_black_to_white_fade_guide = LevelSlide(
    notes=[
        LevelNote(
            beat=31.0,
            lane=-5.0,
            size=0.5,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=0.0,
            segment_green=0.0,
            segment_blue=0.0,
            segment_alpha=0.0,
            connector_ease=EaseType.IN_OUT_QUAD,
        ),
        LevelNote(
            beat=47.0,
            lane=5.0,
            size=1.5,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=1.0,
            segment_green=1.0,
            segment_blue=1.0,
            segment_alpha=1.0,
        ),
    ]
)

long_blue_to_yellow_fade_guide = LevelSlide(
    notes=[
        LevelNote(
            beat=33.0,
            lane=5.0,
            size=1.5,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=0.0,
            segment_green=0.0,
            segment_blue=1.0,
            segment_alpha=1.0,
            connector_ease=EaseType.OUT_IN_QUAD,
        ),
        LevelNote(
            beat=49.0,
            lane=-5.0,
            size=0.5,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=1.0,
            segment_green=1.0,
            segment_blue=0.0,
            segment_alpha=0.0,
        ),
    ]
)

level = build_level(
    name="test",
    title="Test",
    bgm=None,
    entities=[
        LevelBpmChange(beat=0.0, bpm=120.0),
        *tap_notes,
        *flick_notes,
        normal_tail_trace_slide,
        critical_tail_trace_slide,
        normal_flick_end_slide,
        critical_flick_end_slide,
        guide,
        short_red_to_cyan_guide,
        short_magenta_to_green_fade_guide,
        long_black_to_white_fade_guide,
        long_blue_to_yellow_fade_guide,
    ],
)


def load_levels():
    yield level
