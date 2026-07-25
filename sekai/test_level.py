from sekai.level_utils import LevelBpmChange, LevelNote, LevelSlide, build_level
from sekai.lib.connector import ConnectorKind
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

level = build_level(
    name="test",
    title="Test",
    bgm=None,
    entities=[
        LevelBpmChange(beat=0.0, bpm=120.0),
        LevelNote(beat=1.0, lane=-2.0, size=1.0, kind=NoteKind.NORM_TAP),
        slide,
        LevelNote(beat=7.0, lane=2.0, size=1.0, kind=NoteKind.CRIT_FLICK),
    ],
)


def load_levels():
    yield level
