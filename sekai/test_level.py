from sekai.level_utils import LevelBpmChange, LevelNote, LevelSlide, build_level
from sekai.lib.connector import ConnectorKind
from sekai.lib.ease import EaseType
from sekai.lib.note import NoteKind

slide = LevelSlide(
    notes=[
        LevelNote(
            beat=2.0,
            lane=-2.0,
            size=1.0,
            kind=NoteKind.NORM_HEAD_TAP,
            segment_kind=ConnectorKind.ACTIVE_NORMAL,
        ),
        LevelNote(
            beat=4.0,
            lane=0.0,
            size=1.0,
            kind=NoteKind.NORM_TICK,
            segment_kind=ConnectorKind.ACTIVE_NORMAL,
        ),
        LevelNote(
            beat=6.0,
            lane=2.0,
            size=1.0,
            kind=NoteKind.NORM_TAIL_RELEASE,
        ),
    ]
)

guide = LevelSlide(
    notes=[
        LevelNote(
            beat=8.0,
            lane=-2.0,
            size=1.0,
            kind=NoteKind.ANCHOR,
            segment_kind=ConnectorKind.GUIDE_GHOST,
            segment_red=1.0,
            segment_green=0.0,
            segment_blue=0.0,
        ),
        LevelNote(
            beat=9.0,
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
            beat=10.0,
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
            beat=12.0,
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
            beat=12.25,
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
            beat=13.0,
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
            beat=13.5,
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
            beat=16.0,
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
            beat=32.0,
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
            beat=18.0,
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
            beat=34.0,
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
        LevelNote(beat=1.0, lane=-2.0, size=1.0, kind=NoteKind.NORM_TAP),
        slide,
        LevelNote(beat=7.0, lane=2.0, size=1.0, kind=NoteKind.CRIT_FLICK),
        guide,
        short_red_to_cyan_guide,
        short_magenta_to_green_fade_guide,
        long_black_to_white_fade_guide,
        long_blue_to_yellow_fade_guide,
    ],
)


def load_levels():
    yield level
