from typing import cast

from sonolus.script.archetype import PreviewArchetype, StandardImport, callback, entity_data
from sonolus.script.timing import beat_to_time

from sekai.lib import archetype_names
from sekai.lib.layer import LAYER_SIM_LINE, get_z
from sekai.lib.timed_line import (
    TIMED_LINE_HEIGHT_SCALE,
    TimedLineKind,
    get_timed_line_lane_bound,
    get_timed_line_sprite,
    is_timed_line_enabled,
)
from sekai.preview.layout import PreviewData, layout_preview_sim_line, time_to_preview_col, time_to_preview_y


class PreviewBaseTimedLine(PreviewArchetype):
    beat: StandardImport.BEAT
    timescale_group: StandardImport.TIMESCALE_GROUP

    kind: TimedLineKind = entity_data()
    target_time: float = entity_data()

    @callback(order=1)
    def preprocess(self):
        self.kind = cast(TimedLineKind, self.key)
        self.target_time = beat_to_time(self.beat)
        if is_timed_line_enabled(self.kind):
            PreviewData.max_time = max(PreviewData.max_time, self.target_time)

    def render(self):
        if not is_timed_line_enabled(self.kind):
            return
        lane_bound = get_timed_line_lane_bound(self.kind)
        col = time_to_preview_col(self.target_time)
        y = time_to_preview_y(self.target_time, col)
        layout = layout_preview_sim_line(
            left_lane=-lane_bound,
            right_lane=lane_bound,
            col=col,
            y=y,
            height_scale=TIMED_LINE_HEIGHT_SCALE,
        )
        get_timed_line_sprite(self.kind).draw(layout, z=get_z(LAYER_SIM_LINE).tuple)


PreviewMeasureLine = PreviewBaseTimedLine.derive(
    archetype_names.MEASURE_LINE,
    is_scored=False,
    key=TimedLineKind.MEASURE,
)
PreviewSkillActivationLine = PreviewBaseTimedLine.derive(
    archetype_names.SKILL_ACTIVATION_LINE,
    is_scored=False,
    key=TimedLineKind.SKILL_ACTIVATION,
)

PREVIEW_TIMED_LINE_ARCHETYPES = (
    PreviewMeasureLine,
    PreviewSkillActivationLine,
)
