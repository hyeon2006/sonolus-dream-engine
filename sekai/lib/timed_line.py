from enum import IntEnum
from typing import assert_never

from sonolus.script.interval import clamp
from sonolus.script.sprite import Sprite

from sekai.lib.layer import LAYER_SIM_LINE, get_z
from sekai.lib.layout import (
    DynamicLayout,
    get_alpha,
    judgment_approach,
    judgment_progress_at_travel,
    layout_perspective_line,
    tilt_width_factor,
)
from sekai.lib.skin import ActiveSkin

TIMED_LINE_HEIGHT_SCALE = 0.5


class TimedLineKind(IntEnum):
    MEASURE = 0
    SKILL_ACTIVATION = 1


def get_timed_line_lane_bound(kind: TimedLineKind) -> float:
    match kind:
        case TimedLineKind.MEASURE:
            return 6.0
        case TimedLineKind.SKILL_ACTIVATION:
            return 6.5
        case _:
            assert_never(kind)


def get_timed_line_sprite(kind: TimedLineKind) -> Sprite:
    result = +Sprite
    match kind:
        case TimedLineKind.MEASURE:
            result @= ActiveSkin.measure_line
        case TimedLineKind.SKILL_ACTIVATION:
            result @= ActiveSkin.skill_activation_line
        case _:
            assert_never(kind)
    return result


def get_timed_line_end_progress(kind: TimedLineKind) -> float:
    match kind:
        case TimedLineKind.MEASURE:
            return judgment_progress_at_travel(DynamicLayout.lane_b)
        case TimedLineKind.SKILL_ACTIVATION:
            return 1.0
        case _:
            assert_never(kind)


def draw_timed_line(kind: TimedLineKind, visual_progress: float, target_time: float) -> None:
    if visual_progress < DynamicLayout.progress_start or visual_progress > DynamicLayout.progress_cutoff:
        return

    progress = clamp(visual_progress, DynamicLayout.progress_start, DynamicLayout.progress_cutoff)
    travel = judgment_approach(progress)
    lane_bound = get_timed_line_lane_bound(kind)
    layout = layout_perspective_line(
        -lane_bound,
        lane_bound,
        travel,
        DynamicLayout.note_h * TIMED_LINE_HEIGHT_SCALE * tilt_width_factor(travel),
    )
    alpha = get_alpha(target_time)
    if alpha <= 0:
        return
    get_timed_line_sprite(kind).draw(
        layout,
        z=get_z(LAYER_SIM_LINE, target_time).tuple,
        a=alpha,
    )
