from typing import cast

from sonolus.script.archetype import PlayArchetype, StandardImport, callback, entity_data
from sonolus.script.runtime import time
from sonolus.script.timing import beat_to_time

from sekai.lib import archetype_names
from sekai.lib.layout import progress_to
from sekai.lib.note import get_visual_spawn_time
from sekai.lib.timed_line import TimedLineKind, draw_timed_line, get_timed_line_end_progress
from sekai.lib.timescale import (
    CompositeTime,
    group_is_identity,
    group_preempt_time,
    group_scaled_time,
    group_time_to_scaled_time,
    resolve_timescale_group,
    update_timescale_group,
)


class BaseTimedLine(PlayArchetype):
    beat: StandardImport.BEAT
    timescale_group: StandardImport.TIMESCALE_GROUP

    kind: TimedLineKind = entity_data()
    timescale_group_index: int = entity_data()
    target_time: float = entity_data()
    target_scaled_time: CompositeTime = entity_data()
    visual_start_time: float = entity_data()
    note_preempt_time: float = entity_data()
    timescale_is_identity: bool = entity_data()
    end_progress: float = entity_data()

    @callback(order=1)
    def preprocess(self):
        self.kind = cast(TimedLineKind, self.key)
        self.timescale_group_index = resolve_timescale_group(self.timescale_group)
        self.target_time = beat_to_time(self.beat)
        self.target_scaled_time = group_time_to_scaled_time(self.timescale_group_index, self.target_time)
        self.note_preempt_time = group_preempt_time(self.timescale_group_index)
        self.timescale_is_identity = group_is_identity(self.timescale_group_index)
        self.end_progress = get_timed_line_end_progress(self.kind)
        self.visual_start_time = get_visual_spawn_time(
            self.timescale_group_index,
            self.target_scaled_time,
            spawn_window_scale=1,
        )

    def spawn_order(self) -> float:
        return self.visual_start_time

    def should_spawn(self) -> bool:
        return time() >= self.visual_start_time

    def update_sequential(self):
        if self.timescale_is_identity:
            return
        update_timescale_group(self.timescale_group_index)

    def update_parallel(self):
        visual_progress = self.visual_progress
        if self.kind == TimedLineKind.SKILL_ACTIVATION and time() > self.target_time:
            self.despawn = True
            return
        if self.kind == TimedLineKind.MEASURE and visual_progress > self.end_progress:
            self.despawn = True
            return
        draw_timed_line(self.kind, visual_progress, self.target_time)

    @property
    def visual_progress(self) -> float:
        if self.timescale_is_identity:
            return progress_to(self.target_time, time(), self.note_preempt_time)
        return progress_to(
            self.target_scaled_time,
            group_scaled_time(self.timescale_group_index),
            self.note_preempt_time,
        )


MeasureLine = BaseTimedLine.derive(
    archetype_names.MEASURE_LINE,
    is_scored=False,
    key=TimedLineKind.MEASURE,
)
SkillActivationLine = BaseTimedLine.derive(
    archetype_names.SKILL_ACTIVATION_LINE,
    is_scored=False,
    key=TimedLineKind.SKILL_ACTIVATION,
)

TIMED_LINE_ARCHETYPES = (
    MeasureLine,
    SkillActivationLine,
)
