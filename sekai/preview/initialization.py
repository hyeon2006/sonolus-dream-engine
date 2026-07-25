from sonolus.script.archetype import PreviewArchetype, callback, imported
from sonolus.script.printing import PrintColor, PrintFormat
from sonolus.script.quad import Quad
from sonolus.script.timing import beat_to_time

from sekai.lib import archetype_names
from sekai.lib.layer import LAYER_BEAT_LINE, get_z
from sekai.lib.level_config import EngineRevision, init_level_config
from sekai.lib.particle import init_particles
from sekai.lib.skin import ActiveSkin, init_skin
from sekai.lib.ui import init_ui
from sekai.preview.layout import (
    PREVIEW_COLUMN_SECS,
    PreviewData,
    PreviewLayout,
    init_preview_layout,
    layout_preview_bar_line,
    print_at_col_top,
)
from sekai.preview.stage import draw_preview_cover, draw_preview_stage


class PreviewInitialization(PreviewArchetype):
    name = archetype_names.INITIALIZATION

    revision: EngineRevision = imported(name="revision", default=EngineRevision.LATEST)

    @callback(order=1)
    def preprocess(self):
        init_level_config(self.revision)
        init_ui()
        init_skin()
        init_particles()

        init_preview_layout()

    def render(self):
        draw_preview_stage()
        draw_preview_cover()
        print_preview_col_head_text()
        draw_beat_lines()


def print_preview_col_head_text():
    combo = 0
    for col in range(PreviewLayout.column_count):
        if col < len(PreviewData.note_counts_by_col):
            combo += PreviewData.note_counts_by_col[col]
            print_at_col_top(combo, col, fmt=PrintFormat.ENTITY_COUNT, color=PrintColor.RED, side="right")
        print_at_col_top((col + 1) * PREVIEW_COLUMN_SECS, col, fmt=PrintFormat.TIME, color=PrintColor.CYAN, side="left")


def draw_beat_lines():
    visible_secs = PreviewLayout.visible_secs
    beat = 0
    while beat_to_time(beat) <= visible_secs:
        for beat_offset, extend_scale in (
            (0, 0.3),
            (0.25, 0.1),
            (0.5, 0.2),
            (0.75, 0.1),
        ):
            t = beat_to_time(beat + beat_offset)
            if t > visible_secs:
                continue
            left_layout = +Quad
            right_layout = +Quad
            left_layout @= layout_preview_bar_line(t, extend="left_only", extend_scale=extend_scale)
            right_layout @= layout_preview_bar_line(t, extend="right_only", extend_scale=extend_scale)
            ActiveSkin.beat_line.draw(left_layout, z=get_z(LAYER_BEAT_LINE).tuple, a=0.5)
            ActiveSkin.beat_line.draw(right_layout, z=get_z(LAYER_BEAT_LINE).tuple, a=0.5)
        beat += 1
