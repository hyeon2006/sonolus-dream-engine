from enum import IntEnum
from math import ceil, cos, pi
from typing import Literal, assert_never

from sonolus.script.archetype import EntityRef
from sonolus.script.easing import ease_out_cubic
from sonolus.script.effect import Effect, LoopedEffectHandle
from sonolus.script.interval import clamp, lerp, remap_clamped, unlerp_clamped
from sonolus.script.particle import Particle, ParticleHandle
from sonolus.script.quad import Quad, QuadLike
from sonolus.script.record import Record
from sonolus.script.runtime import time
from sonolus.script.sprite import Sprite
from sonolus.script.timing import beat_to_time

from sekai.lib.buckets import SLIDE_TICK_JUDGMENT_WINDOW
from sekai.lib.ease import EaseType, ease
from sekai.lib.effect import Effects
from sekai.lib.layer import (
    LAYER_ACTIVE_SLIDE_CONNECTOR,
    LAYER_GUIDE_CONNECTOR,
    LAYER_SLOT_GLOW_EFFECT,
    ZIndexes,
    get_z,
)
from sekai.lib.layout import (
    AffineTransform2d,
    DynamicLayout,
    approach,
    get_alpha,
    iter_slot_lanes,
    layout_circular_effect,
    layout_linear_effect,
    layout_slide_connector_segment,
    layout_slot_glow_effect,
    pre_rotation_vec_at,
)
from sekai.lib.options import Options
from sekai.lib.particle import ActiveParticles
from sekai.lib.skin import ActiveConnectorSpriteSet, ActiveSkin
from sekai.lib.timescale import iter_timescale_changes_in_group_from_time

CONNECTOR_TRAIL_SPAWN_PERIOD = 0.1
CONNECTOR_SLOT_SPAWN_PERIOD = 0.2
CONNECTOR_THROUGH_JUDGE_LINE_DESPAWN_DELAY = 5.0
CONNECTOR_LENIENCY = 1
GUIDE_CONNECTOR_BLEND_PATH_SAMPLES = 8
GUIDE_CONNECTOR_BLEND_PATH_SEGMENTS = 128


class ConnectorKind(IntEnum):
    NONE = 0

    ACTIVE_NORMAL = 1
    ACTIVE_CRITICAL = 2
    DAMAGE = 3
    ACTIVE_FAKE_NORMAL = 51
    ACTIVE_FAKE_CRITICAL = 52
    FAKE_DAMAGE = 53

    # Use GUIDE_GHOST with explicit RGB values by default unless a predefined
    # guide palette kind is required for a specific compatibility reason.
    GUIDE_GHOST = 100
    GUIDE_NEUTRAL = 101
    GUIDE_RED = 102
    GUIDE_GREEN = 103
    GUIDE_BLUE = 104
    GUIDE_YELLOW = 105
    GUIDE_PURPLE = 106
    GUIDE_CYAN = 107
    GUIDE_BLACK = 108


ActiveConnectorKind = Literal[
    ConnectorKind.ACTIVE_NORMAL,
    ConnectorKind.ACTIVE_CRITICAL,
    ConnectorKind.ACTIVE_FAKE_NORMAL,
    ConnectorKind.ACTIVE_FAKE_CRITICAL,
]

GuideConnectorKind = Literal[
    ConnectorKind.GUIDE_GHOST,
    ConnectorKind.GUIDE_NEUTRAL,
    ConnectorKind.GUIDE_RED,
    ConnectorKind.GUIDE_GREEN,
    ConnectorKind.GUIDE_BLUE,
    ConnectorKind.GUIDE_YELLOW,
    ConnectorKind.GUIDE_PURPLE,
    ConnectorKind.GUIDE_CYAN,
    ConnectorKind.GUIDE_BLACK,
]


class GuideColor(Record):
    red: float
    green: float
    blue: float


class ConnectorVisualState(IntEnum):
    WAITING = 0
    INACTIVE = 1
    ACTIVE = 2


def is_fake_active_connector(kind: ConnectorKind) -> bool:
    return kind in {ConnectorKind.ACTIVE_FAKE_NORMAL, ConnectorKind.ACTIVE_FAKE_CRITICAL}


def is_fake_connector(kind: ConnectorKind) -> bool:
    return is_fake_active_connector(kind) or kind == ConnectorKind.FAKE_DAMAGE


def is_guide_connector(kind: ConnectorKind) -> bool:
    return kind in {
        ConnectorKind.GUIDE_GHOST,
        ConnectorKind.GUIDE_NEUTRAL,
        ConnectorKind.GUIDE_RED,
        ConnectorKind.GUIDE_GREEN,
        ConnectorKind.GUIDE_BLUE,
        ConnectorKind.GUIDE_YELLOW,
        ConnectorKind.GUIDE_PURPLE,
        ConnectorKind.GUIDE_CYAN,
        ConnectorKind.GUIDE_BLACK,
    }


def get_guide_connector_color(kind: ConnectorKind) -> GuideColor:
    result = +GuideColor
    match kind:
        case ConnectorKind.GUIDE_GHOST | ConnectorKind.GUIDE_NEUTRAL:
            result @= GuideColor(red=1.0, green=1.0, blue=1.0)
        case ConnectorKind.GUIDE_RED:
            result @= GuideColor(red=1.0, green=0.0, blue=0.0)
        case ConnectorKind.GUIDE_GREEN:
            result @= GuideColor(red=0.0, green=1.0, blue=0.0)
        case ConnectorKind.GUIDE_BLUE:
            result @= GuideColor(red=0.0, green=0.0, blue=1.0)
        case ConnectorKind.GUIDE_YELLOW:
            result @= GuideColor(red=1.0, green=1.0, blue=0.0)
        case ConnectorKind.GUIDE_PURPLE:
            result @= GuideColor(red=1.0, green=0.0, blue=1.0)
        case ConnectorKind.GUIDE_CYAN:
            result @= GuideColor(red=0.0, green=1.0, blue=1.0)
        case ConnectorKind.GUIDE_BLACK:
            result @= GuideColor(red=0.0, green=0.0, blue=0.0)
        case _:
            result @= GuideColor(red=1.0, green=1.0, blue=1.0)
    return result


def resolve_guide_connector_color(
    kind: ConnectorKind,
    red: float,
    green: float,
    blue: float,
) -> GuideColor:
    fallback = get_guide_connector_color(kind)
    return GuideColor(
        red=clamp(red, 0.0, 1.0) if red >= 0.0 else fallback.red,
        green=clamp(green, 0.0, 1.0) if green >= 0.0 else fallback.green,
        blue=clamp(blue, 0.0, 1.0) if blue >= 0.0 else fallback.blue,
    )


def should_show_connector_hitbox(kind: ConnectorKind) -> bool:
    # DAMAGE is input-tracked but excluded: its region is already visualized by the tick
    # hitboxes, which follow the head and would coincide with a connector-level overlay.
    return kind in {ConnectorKind.ACTIVE_NORMAL, ConnectorKind.ACTIVE_CRITICAL}


def get_connector_input_leniency(kind: ConnectorKind) -> float:
    if kind == ConnectorKind.DAMAGE:
        return 0.0
    return CONNECTOR_LENIENCY


def get_active_connector_sprites(kind: ActiveConnectorKind) -> ActiveConnectorSpriteSet:
    result = +ActiveConnectorSpriteSet
    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            result @= ActiveSkin.active_slide_connector
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            result @= ActiveSkin.critical_active_slide_connector
        case _:
            assert_never(kind)
    return result


def get_guide_connector_sprite(kind: GuideConnectorKind) -> Sprite:
    result = +Sprite
    match kind:
        case ConnectorKind.GUIDE_GHOST | ConnectorKind.GUIDE_NEUTRAL:
            result @= ActiveSkin.guide_neutral
        case ConnectorKind.GUIDE_RED:
            result @= ActiveSkin.guide_red
        case ConnectorKind.GUIDE_GREEN:
            result @= ActiveSkin.guide_green
        case ConnectorKind.GUIDE_BLUE:
            result @= ActiveSkin.guide_blue
        case ConnectorKind.GUIDE_YELLOW:
            result @= ActiveSkin.guide_yellow
        case ConnectorKind.GUIDE_PURPLE:
            result @= ActiveSkin.guide_purple
        case ConnectorKind.GUIDE_CYAN:
            result @= ActiveSkin.guide_cyan
        case ConnectorKind.GUIDE_BLACK:
            result @= ActiveSkin.guide_black
        case _:
            assert_never(kind)
    return result


def get_damage_connector_sprite() -> Sprite:
    result = +Sprite
    result @= ActiveSkin.damage_slide_connector
    return result


def get_damage_connector_active_sprite() -> Sprite:
    result = +Sprite
    result @= ActiveSkin.damage_slide_connector_active
    return result


def get_connector_z(kind: ConnectorKind, target_time: float, lane: float, active: bool) -> ZIndexes:
    result = +ZIndexes
    match kind:
        case (
            ConnectorKind.ACTIVE_NORMAL
            | ConnectorKind.ACTIVE_FAKE_NORMAL
            | ConnectorKind.ACTIVE_CRITICAL
            | ConnectorKind.ACTIVE_FAKE_CRITICAL
        ):
            result @= get_z(
                LAYER_ACTIVE_SLIDE_CONNECTOR,
                time=target_time,
                lane=lane,
                etc=get_active_connector_z_offset(kind, active),
                invert_time=True,
            )
        case (
            ConnectorKind.GUIDE_GHOST
            | ConnectorKind.GUIDE_NEUTRAL
            | ConnectorKind.GUIDE_RED
            | ConnectorKind.GUIDE_GREEN
            | ConnectorKind.GUIDE_BLUE
            | ConnectorKind.GUIDE_YELLOW
            | ConnectorKind.GUIDE_PURPLE
            | ConnectorKind.GUIDE_CYAN
            | ConnectorKind.GUIDE_BLACK
        ):
            result @= get_z(
                LAYER_GUIDE_CONNECTOR,
                time=target_time,
                lane=lane,
                etc=0 if kind == ConnectorKind.GUIDE_GHOST else kind - ConnectorKind.GUIDE_NEUTRAL,
                invert_time=True,
            )
        case ConnectorKind.DAMAGE | ConnectorKind.FAKE_DAMAGE:
            result @= get_z(
                LAYER_GUIDE_CONNECTOR,
                time=target_time,
                lane=lane,
                etc=get_active_connector_z_offset(kind, active),
                invert_time=True,
            )
        case ConnectorKind.NONE:
            pass
        case _:
            assert_never(kind)
    return result


def get_active_connector_z_offset(
    kind: ActiveConnectorKind | Literal[ConnectorKind.DAMAGE, ConnectorKind.FAKE_DAMAGE], active: bool
) -> int:
    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            return 3 - active
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            return 1 - active
        case ConnectorKind.DAMAGE | ConnectorKind.FAKE_DAMAGE:
            return 9 - active
        case _:
            assert_never(kind)


def get_connector_alpha_option(kind: ConnectorKind) -> float:
    match kind:
        case (
            ConnectorKind.ACTIVE_NORMAL
            | ConnectorKind.ACTIVE_FAKE_NORMAL
            | ConnectorKind.ACTIVE_CRITICAL
            | ConnectorKind.ACTIVE_FAKE_CRITICAL
        ):
            return Options.slide_alpha
        case ConnectorKind.DAMAGE | ConnectorKind.FAKE_DAMAGE:
            return Options.slide_alpha
        case (
            ConnectorKind.GUIDE_GHOST
            | ConnectorKind.GUIDE_NEUTRAL
            | ConnectorKind.GUIDE_RED
            | ConnectorKind.GUIDE_GREEN
            | ConnectorKind.GUIDE_BLUE
            | ConnectorKind.GUIDE_YELLOW
            | ConnectorKind.GUIDE_PURPLE
            | ConnectorKind.GUIDE_CYAN
            | ConnectorKind.GUIDE_BLACK
        ):
            return Options.guide_alpha
        case ConnectorKind.NONE:
            return 0.0
        case _:
            assert_never(kind)


def get_connector_quality_option(kind: ConnectorKind) -> float:
    match kind:
        case (
            ConnectorKind.ACTIVE_NORMAL
            | ConnectorKind.ACTIVE_FAKE_NORMAL
            | ConnectorKind.ACTIVE_CRITICAL
            | ConnectorKind.ACTIVE_FAKE_CRITICAL
        ):
            return Options.slide_quality
        case ConnectorKind.DAMAGE | ConnectorKind.FAKE_DAMAGE:
            return Options.slide_quality
        case (
            ConnectorKind.GUIDE_GHOST
            | ConnectorKind.GUIDE_NEUTRAL
            | ConnectorKind.GUIDE_RED
            | ConnectorKind.GUIDE_GREEN
            | ConnectorKind.GUIDE_BLUE
            | ConnectorKind.GUIDE_YELLOW
            | ConnectorKind.GUIDE_PURPLE
            | ConnectorKind.GUIDE_CYAN
            | ConnectorKind.GUIDE_BLACK
        ):
            return Options.guide_quality
        case ConnectorKind.NONE:
            return 0
        case _:
            assert_never(kind)


def draw_connector(
    kind: ConnectorKind,
    visual_state: ConnectorVisualState,
    ease_type: EaseType,
    head_lane: float,
    head_size: float,
    head_visual_progress: float,
    head_target_time: float,
    head_ease_frac: float,
    tail_lane: float,
    tail_size: float,
    tail_visual_progress: float,
    tail_target_time: float,
    tail_ease_frac: float,
    segment_head_target_time: float,
    segment_head_lane: float,
    segment_head_red: float,
    segment_head_green: float,
    segment_head_blue: float,
    segment_head_alpha: float,
    segment_tail_target_time: float,
    segment_tail_red: float,
    segment_tail_green: float,
    segment_tail_blue: float,
    segment_tail_alpha: float,
):
    if (
        (head_visual_progress < DynamicLayout.progress_start and tail_visual_progress < DynamicLayout.progress_start)
        or (
            head_visual_progress > DynamicLayout.progress_cutoff
            and tail_visual_progress > DynamicLayout.progress_cutoff
        )
        or head_visual_progress == tail_visual_progress
    ):
        return

    if Options.disable_fake_notes and is_fake_connector(kind):
        return

    if ease_type == EaseType.NONE:
        tail_lane = head_lane
        tail_size = head_size

    segment_head_color = resolve_guide_connector_color(
        kind,
        segment_head_red,
        segment_head_green,
        segment_head_blue,
    )
    segment_tail_color = resolve_guide_connector_color(
        kind,
        segment_tail_red,
        segment_tail_green,
        segment_tail_blue,
    )

    normal_sprite = Sprite(-1)
    active_sprite = Sprite(-1)
    match kind:
        case (
            ConnectorKind.ACTIVE_NORMAL
            | ConnectorKind.ACTIVE_CRITICAL
            | ConnectorKind.ACTIVE_FAKE_NORMAL
            | ConnectorKind.ACTIVE_FAKE_CRITICAL
        ):
            sprites = get_active_connector_sprites(kind)
            normal_sprite @= sprites.connection.normal
            active_sprite @= sprites.connection.active
        case (
            ConnectorKind.GUIDE_GHOST
            | ConnectorKind.GUIDE_NEUTRAL
            | ConnectorKind.GUIDE_RED
            | ConnectorKind.GUIDE_GREEN
            | ConnectorKind.GUIDE_BLUE
            | ConnectorKind.GUIDE_YELLOW
            | ConnectorKind.GUIDE_PURPLE
            | ConnectorKind.GUIDE_CYAN
            | ConnectorKind.GUIDE_BLACK
        ):
            sprites = get_guide_connector_sprite(kind)
            normal_sprite @= sprites
        case ConnectorKind.DAMAGE:
            normal_sprite @= get_damage_connector_sprite()
            active_sprite @= get_damage_connector_active_sprite()
        case ConnectorKind.FAKE_DAMAGE:
            normal_sprite @= get_damage_connector_sprite()
        case ConnectorKind.NONE:
            return
        case _:
            assert_never(kind)

    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_CRITICAL:
            segment_head_alpha = 1.0
            segment_tail_alpha = 1.0
        case ConnectorKind.ACTIVE_FAKE_NORMAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            segment_head_alpha = 1.0
            segment_tail_alpha = 1.0
            if visual_state == ConnectorVisualState.INACTIVE:
                visual_state = ConnectorVisualState.ACTIVE
        case (
            ConnectorKind.GUIDE_GHOST
            | ConnectorKind.GUIDE_NEUTRAL
            | ConnectorKind.GUIDE_RED
            | ConnectorKind.GUIDE_GREEN
            | ConnectorKind.GUIDE_BLUE
            | ConnectorKind.GUIDE_YELLOW
            | ConnectorKind.GUIDE_PURPLE
            | ConnectorKind.GUIDE_CYAN
            | ConnectorKind.GUIDE_BLACK
            | ConnectorKind.FAKE_DAMAGE
        ):
            visual_state = ConnectorVisualState.WAITING
        case ConnectorKind.DAMAGE:
            pass
        case _:
            assert_never(kind)

    head_alpha = remap_clamped(
        segment_head_target_time, segment_tail_target_time, segment_head_alpha, segment_tail_alpha, head_target_time
    )
    tail_alpha = remap_clamped(
        segment_head_target_time, segment_tail_target_time, segment_head_alpha, segment_tail_alpha, tail_target_time
    )
    head_red = remap_clamped(
        segment_head_target_time,
        segment_tail_target_time,
        segment_head_color.red,
        segment_tail_color.red,
        head_target_time,
    )
    head_green = remap_clamped(
        segment_head_target_time,
        segment_tail_target_time,
        segment_head_color.green,
        segment_tail_color.green,
        head_target_time,
    )
    head_blue = remap_clamped(
        segment_head_target_time,
        segment_tail_target_time,
        segment_head_color.blue,
        segment_tail_color.blue,
        head_target_time,
    )
    tail_red = remap_clamped(
        segment_head_target_time,
        segment_tail_target_time,
        segment_head_color.red,
        segment_tail_color.red,
        tail_target_time,
    )
    tail_green = remap_clamped(
        segment_head_target_time,
        segment_tail_target_time,
        segment_head_color.green,
        segment_tail_color.green,
        tail_target_time,
    )
    tail_blue = remap_clamped(
        segment_head_target_time,
        segment_tail_target_time,
        segment_head_color.blue,
        segment_tail_color.blue,
        tail_target_time,
    )

    if time() >= tail_target_time and not is_guide_connector(kind):
        return

    z_normal = get_connector_z(kind, segment_head_target_time, segment_head_lane, active=False)
    z_active = +ZIndexes
    if visual_state == ConnectorVisualState.ACTIVE and active_sprite.is_available:
        z_active @= get_connector_z(kind, segment_head_target_time, segment_head_lane, active=True)
    else:
        z_active @= z_normal

    draw_connector_default(
        kind=kind,
        visual_state=visual_state,
        ease_type=ease_type,
        normal_sprite=normal_sprite,
        active_sprite=active_sprite,
        z_normal=z_normal,
        z_active=z_active,
        head_lane=head_lane,
        head_size=head_size,
        head_visual_progress=head_visual_progress,
        head_target_time=head_target_time,
        head_ease_frac=head_ease_frac,
        head_red=head_red,
        head_green=head_green,
        head_blue=head_blue,
        head_alpha=head_alpha,
        tail_lane=tail_lane,
        tail_size=tail_size,
        tail_visual_progress=tail_visual_progress,
        tail_target_time=tail_target_time,
        tail_ease_frac=tail_ease_frac,
        tail_red=tail_red,
        tail_green=tail_green,
        tail_blue=tail_blue,
        tail_alpha=tail_alpha,
    )


def draw_connector_default(
    kind: ConnectorKind,
    visual_state: ConnectorVisualState,
    ease_type: EaseType,
    normal_sprite: Sprite,
    active_sprite: Sprite,
    z_normal: ZIndexes,
    z_active: ZIndexes,
    head_lane: float,
    head_size: float,
    head_visual_progress: float,
    head_target_time: float,
    head_ease_frac: float,
    head_red: float,
    head_green: float,
    head_blue: float,
    head_alpha: float,
    tail_lane: float,
    tail_size: float,
    tail_visual_progress: float,
    tail_target_time: float,
    tail_ease_frac: float,
    tail_red: float,
    tail_green: float,
    tail_blue: float,
    tail_alpha: float,
):
    is_guide = is_guide_connector(kind)
    start_visual_progress = clamp(head_visual_progress, DynamicLayout.progress_start, DynamicLayout.progress_cutoff)
    end_visual_progress = clamp(tail_visual_progress, DynamicLayout.progress_start, DynamicLayout.progress_cutoff)
    start_frac = unlerp_clamped(head_visual_progress, tail_visual_progress, start_visual_progress)
    end_frac = unlerp_clamped(head_visual_progress, tail_visual_progress, end_visual_progress)
    start_ease_frac = lerp(head_ease_frac, tail_ease_frac, start_frac)
    end_ease_frac = lerp(head_ease_frac, tail_ease_frac, end_frac)
    eased_head_ease_frac = ease(ease_type, head_ease_frac)
    eased_tail_ease_frac = ease(ease_type, tail_ease_frac)
    start_interp_frac = unlerp_clamped(eased_head_ease_frac, eased_tail_ease_frac, ease(ease_type, start_ease_frac))
    end_interp_frac = unlerp_clamped(eased_head_ease_frac, eased_tail_ease_frac, ease(ease_type, end_ease_frac))
    start_travel = approach(start_visual_progress)
    end_travel = approach(end_visual_progress)
    start_lane = lerp(head_lane, tail_lane, start_interp_frac)
    end_lane = lerp(head_lane, tail_lane, end_interp_frac)
    start_size = max(1e-3, lerp(head_size, tail_size, start_interp_frac))  # Lightweight rendering needs >0 size.
    end_size = max(1e-3, lerp(head_size, tail_size, end_interp_frac))  # Lightweight rendering needs >0 size.
    start_red = 0.0
    start_green = 0.0
    start_blue = 0.0
    if is_guide:
        start_red = lerp(head_red, tail_red, start_frac)
        start_green = lerp(head_green, tail_green, start_frac)
        start_blue = lerp(head_blue, tail_blue, start_frac)
    start_alpha = lerp(head_alpha, tail_alpha, start_frac)
    end_alpha = lerp(head_alpha, tail_alpha, end_frac)
    start_pos_y = pre_rotation_vec_at(start_lane, start_travel).y
    end_pos_y = pre_rotation_vec_at(end_lane, end_travel).y

    match ease_type:
        case EaseType.NONE:
            curve_change_scale = 0.0
        case EaseType.LINEAR:
            x_diff = (
                max(
                    abs((start_lane - start_size) - (end_lane - end_size)),
                    abs((start_lane + start_size) - (end_lane + end_size)),
                )
                * DynamicLayout.w_scale
            )
            y_diff = abs(start_pos_y - end_pos_y)
            travel_adj = clamp(2 - max(start_travel, end_travel), 1, 2)
            curve_change_scale = (min(x_diff, y_diff) * travel_adj) * 0.8
        case _:
            left_start_lane = start_lane - start_size
            left_end_lane = end_lane - end_size
            right_start_lane = start_lane + start_size
            right_end_lane = end_lane + end_size
            if abs(start_size - end_size) < 0.1:
                ref_start_lane = start_lane
                ref_end_lane = end_lane
                ref_head_lane = head_lane
                ref_tail_lane = tail_lane
            elif abs(left_start_lane - left_end_lane) > abs(right_start_lane - right_end_lane):
                ref_start_lane = left_start_lane
                ref_end_lane = left_end_lane
                ref_head_lane = head_lane - head_size
                ref_tail_lane = tail_lane - tail_size
            else:
                ref_start_lane = right_start_lane
                ref_end_lane = right_end_lane
                ref_head_lane = head_lane + head_size
                ref_tail_lane = tail_lane + tail_size
            start_ref = pre_rotation_vec_at(ref_start_lane, start_travel)
            end_ref = pre_rotation_vec_at(ref_end_lane, end_travel)
            last_pos_offset = 0
            total_pos_offsets = 0
            for r in (0.25, 0.75):
                ease_frac = lerp(start_ease_frac, end_ease_frac, r)
                interp_frac = unlerp_clamped(eased_head_ease_frac, eased_tail_ease_frac, ease(ease_type, ease_frac))
                visual_progress = lerp(start_visual_progress, end_visual_progress, r)
                travel = approach(visual_progress)
                lane = lerp(ref_head_lane, ref_tail_lane, interp_frac)
                pos = pre_rotation_vec_at(lane, travel)
                ref_pos = lerp(start_ref, end_ref, unlerp_clamped(start_travel, end_travel, travel))
                current_pos_offset = pos.x - ref_pos.x
                total_pos_offsets += abs(current_pos_offset - last_pos_offset) ** 0.6
                last_pos_offset = current_pos_offset
            total_pos_offsets += abs(last_pos_offset) ** 0.6
            curve_change_scale = total_pos_offsets * 1.5
    alpha_change_delta = min(abs(start_alpha - end_alpha) * get_connector_alpha_option(kind), 1.0)
    alpha_change_scale = max(
        alpha_change_delta**0.8 * 3,
        alpha_change_delta**0.5 * abs(start_pos_y - end_pos_y) * 3,
    )
    rgba_segment_count = 0.0
    if is_guide:
        rgba_segment_count = get_guide_blended_rgba_segment_count(
            head_red,
            head_green,
            head_blue,
            head_alpha,
            tail_red,
            tail_green,
            tail_blue,
            tail_alpha,
            get_connector_alpha_option(kind),
        )
    quality = get_connector_quality_option(kind)
    segment_count = max(
        1,
        ceil(max(curve_change_scale, alpha_change_scale) * quality * 10),
        ceil(rgba_segment_count * quality),
    )

    last_travel = start_travel
    last_lane = start_lane
    last_size = start_size
    last_red = start_red
    last_green = start_green
    last_blue = start_blue
    last_alpha = start_alpha
    last_target_time = lerp(head_target_time, tail_target_time, start_frac)

    layout = +Quad
    for i in range(1, segment_count + 1):
        segment_frac = i / segment_count
        next_frac = lerp(start_frac, end_frac, segment_frac)
        next_ease_frac = lerp(start_ease_frac, end_ease_frac, segment_frac)
        next_interp_frac = unlerp_clamped(eased_head_ease_frac, eased_tail_ease_frac, ease(ease_type, next_ease_frac))
        next_visual_progress = lerp(start_visual_progress, end_visual_progress, segment_frac)
        next_travel = approach(next_visual_progress)
        next_lane = lerp(head_lane, tail_lane, next_interp_frac)
        next_size = max(1e-3, lerp(head_size, tail_size, next_interp_frac))
        next_red = 0.0
        next_green = 0.0
        next_blue = 0.0
        if is_guide:
            next_red = lerp(head_red, tail_red, next_frac)
            next_green = lerp(head_green, tail_green, next_frac)
            next_blue = lerp(head_blue, tail_blue, next_frac)
        next_alpha = lerp(head_alpha, tail_alpha, next_frac)
        next_target_time = lerp(head_target_time, tail_target_time, next_frac)

        base_a = clamp(
            get_alpha((last_target_time + next_target_time) / 2)
            * (last_alpha + next_alpha)
            / 2
            * get_connector_alpha_option(kind),
            0,
            1,
        )

        layout @= layout_slide_connector_segment(
            start_lane=last_lane,
            start_size=last_size,
            start_travel=last_travel,
            end_lane=next_lane,
            end_size=next_size,
            end_travel=next_travel,
        )

        if is_guide:
            draw_guide_connector_quad(
                layout,
                z_normal,
                (last_red + next_red) / 2,
                (last_green + next_green) / 2,
                (last_blue + next_blue) / 2,
                base_a,
            )
        else:
            draw_connector_quad(layout, visual_state, normal_sprite, active_sprite, z_normal, z_active, base_a)

        last_travel = next_travel
        last_lane = next_lane
        last_size = next_size
        last_red = next_red
        last_green = next_green
        last_blue = next_blue
        last_alpha = next_alpha
        last_target_time = next_target_time


def get_guide_blended_rgba_segment_count(
    head_red: float,
    head_green: float,
    head_blue: float,
    head_alpha: float,
    tail_red: float,
    tail_green: float,
    tail_blue: float,
    tail_alpha: float,
    alpha_multiplier: float,
) -> float:
    last_alpha = clamp(head_alpha * alpha_multiplier, 0.0, 1.0)
    last_black_red = last_alpha * head_red
    last_black_green = last_alpha * head_green
    last_black_blue = last_alpha * head_blue
    last_white_red = last_black_red + 1 - last_alpha
    last_white_green = last_black_green + 1 - last_alpha
    last_white_blue = last_black_blue + 1 - last_alpha
    blend_path_length = 0.0

    # Source-over differences are largest against either black or white.
    # Sampling both also captures the quadratic path from RGBA interpolation.
    for i in range(1, GUIDE_CONNECTOR_BLEND_PATH_SAMPLES + 1):
        frac = i / GUIDE_CONNECTOR_BLEND_PATH_SAMPLES
        red = lerp(head_red, tail_red, frac)
        green = lerp(head_green, tail_green, frac)
        blue = lerp(head_blue, tail_blue, frac)
        alpha = clamp(lerp(head_alpha, tail_alpha, frac) * alpha_multiplier, 0.0, 1.0)
        black_red = alpha * red
        black_green = alpha * green
        black_blue = alpha * blue
        white_red = black_red + 1 - alpha
        white_green = black_green + 1 - alpha
        white_blue = black_blue + 1 - alpha
        blend_path_length += max(
            abs(black_red - last_black_red),
            abs(black_green - last_black_green),
            abs(black_blue - last_black_blue),
            abs(white_red - last_white_red),
            abs(white_green - last_white_green),
            abs(white_blue - last_white_blue),
        )
        last_black_red = black_red
        last_black_green = black_green
        last_black_blue = black_blue
        last_white_red = white_red
        last_white_green = white_green
        last_white_blue = white_blue

    return blend_path_length * GUIDE_CONNECTOR_BLEND_PATH_SEGMENTS


def draw_guide_connector_quad(
    layout: QuadLike,
    z: ZIndexes,
    red: float,
    green: float,
    blue: float,
    alpha: float,
):
    red = clamp(red, 0.0, 1.0)
    green = clamp(green, 0.0, 1.0)
    blue = clamp(blue, 0.0, 1.0)
    alpha = clamp(alpha, 0.0, 1.0)

    # Trilinear weights over the eight RGB cube corners.
    black = alpha * (1 - red) * (1 - green) * (1 - blue)
    red_only = alpha * red * (1 - green) * (1 - blue)
    green_only = alpha * (1 - red) * green * (1 - blue)
    blue_only = alpha * (1 - red) * (1 - green) * blue
    yellow = alpha * red * green * (1 - blue)
    magenta = alpha * red * (1 - green) * blue
    cyan = alpha * (1 - red) * green * blue
    neutral = alpha * red * green * blue

    prefix = black
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_BLACK, black, alpha, prefix, 0)
    prefix += red_only
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_RED, red_only, alpha, prefix, 1)
    prefix += green_only
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_GREEN, green_only, alpha, prefix, 2)
    prefix += blue_only
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_BLUE, blue_only, alpha, prefix, 3)
    prefix += yellow
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_YELLOW, yellow, alpha, prefix, 4)
    prefix += magenta
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_PURPLE, magenta, alpha, prefix, 5)
    prefix += cyan
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_CYAN, cyan, alpha, prefix, 6)
    prefix += neutral
    draw_guide_connector_color_layer(layout, z, ConnectorKind.GUIDE_NEUTRAL, neutral, alpha, prefix, 7)


def draw_guide_connector_color_layer(
    layout: QuadLike,
    z: ZIndexes,
    kind: GuideConnectorKind,
    contribution: float,
    total_alpha: float,
    prefix: float,
    order: int,
):
    if contribution <= 0.0:
        return
    # Convert the desired premultiplied contribution into a source-over layer alpha.
    layer_alpha = contribution / max(1e-6, 1 - total_alpha + prefix)
    get_guide_connector_sprite(kind).draw(
        layout,
        z=(z.z1, z.z2, z.z3, z.z4 + order / 1000),
        a=layer_alpha,
    )


def draw_connector_quad(
    layout: QuadLike,
    visual_state: ConnectorVisualState,
    normal_sprite: Sprite,
    active_sprite: Sprite,
    z_normal: ZIndexes,
    z_active: ZIndexes,
    base_a: float,
):
    if visual_state == ConnectorVisualState.ACTIVE and active_sprite.is_available:
        if Options.connector_animation:
            a_modifier = (cos(2 * pi * time()) + 1) / 2
            normal_sprite.draw(layout, z=z_normal.tuple, a=base_a * ease_out_cubic(a_modifier))
            active_sprite.draw(layout, z=z_active.tuple, a=base_a * ease_out_cubic(1 - a_modifier))
        else:
            active_sprite.draw(layout, z=z_active.tuple, a=base_a)
    else:
        normal_sprite.draw(
            layout, z=z_normal.tuple, a=base_a * (1 if visual_state != ConnectorVisualState.INACTIVE else 0.5)
        )


class ActiveConnectorInfo(Record):
    visual_lane: float
    visual_size: float
    input_bounds: Quad
    active_start_time: float
    last_active_time: float
    connector_kind: ConnectorKind

    @property
    def is_active(self) -> bool:
        return self.last_active_time >= (SLIDE_TICK_JUDGMENT_WINDOW.perfect + time()).start


def update_circular_connector_particle(
    handle: ParticleHandle,
    kind: ActiveConnectorKind,
    lane: float,
    replace: bool,
    *,
    transform: AffineTransform2d,
):
    if not Options.note_effect_enabled:
        return
    layout = transform.transform_quad(layout_circular_effect(lane, w=3.5, h=2.1))
    if replace or handle.id == 0:
        particle = +Particle(-1)
        match kind:
            case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
                particle @= ActiveParticles.normal_slide_connector.circular
            case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
                particle @= ActiveParticles.critical_slide_connector.circular
            case _:
                assert_never(kind)
        replace_looped_particle(handle, particle, layout, duration=1)
    else:
        update_looped_particle(handle, layout)


def update_linear_connector_particle(
    handle: ParticleHandle,
    kind: ActiveConnectorKind,
    lane: float,
    replace: bool,
    *,
    transform: AffineTransform2d,
):
    if not Options.note_effect_enabled:
        return
    layout = transform.transform_quad(layout_linear_effect(lane, shear=0))
    particle = +Particle
    if replace or handle.id == 0:
        match kind:
            case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
                particle @= ActiveParticles.normal_slide_connector.linear
            case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
                particle @= ActiveParticles.critical_slide_connector.linear
            case _:
                assert_never(kind)
        replace_looped_particle(handle, particle, layout, duration=1)
    else:
        update_looped_particle(handle, layout)


def spawn_linear_connector_trail_particle(
    kind: ActiveConnectorKind,
    lane: float,
    *,
    transform: AffineTransform2d,
):
    if not Options.note_effect_enabled:
        return
    layout = transform.transform_quad(layout_linear_effect(lane, shear=0))
    particle = +Particle
    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            particle @= ActiveParticles.normal_slide_connector.trail_linear
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            particle @= ActiveParticles.critical_slide_connector.trail_linear
        case _:
            assert_never(kind)
    particle.spawn(layout, duration=0.5 / Options.effect_animation_speed)


def spawn_connector_slot_particles(
    kind: ActiveConnectorKind,
    lane: float,
    size: float,
    *,
    transform: AffineTransform2d,
):
    if not Options.note_effect_enabled:
        return
    particle = +Particle
    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            particle @= ActiveParticles.normal_slide_connector.slot_linear
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            particle @= ActiveParticles.critical_slide_connector.slot_linear
        case _:
            assert_never(kind)
    for slot_lane in iter_slot_lanes(lane, size):
        layout = transform.transform_quad(layout_linear_effect(slot_lane, shear=0))
        particle.spawn(layout, duration=0.5 / Options.effect_animation_speed)


def draw_connector_slot_glow_effect(
    kind: ActiveConnectorKind,
    start_time: float,
    lane: float,
    size: float,
    *,
    transform: AffineTransform2d,
):
    sprite = +Sprite
    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            sprite @= ActiveSkin.active_slide_connector.slot_glow
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            sprite @= ActiveSkin.critical_active_slide_connector.slot_glow
        case _:
            assert_never(kind)
    height = (3.25 + (cos((time() - start_time) * 8 * pi) + 1) / 2) / 4.25
    layout = transform.transform_quad(layout_slot_glow_effect(lane, size, height))
    z = get_z(LAYER_SLOT_GLOW_EFFECT, start_time, lane, invert_time=True)
    a = remap_clamped(start_time, start_time + 0.25, 0.0, 0.3, time())
    sprite.draw(layout, z=z.tuple, a=a)


def update_connector_sfx(
    handle: LoopedEffectHandle,
    kind: ActiveConnectorKind,
    replace: bool,
):
    if not Options.sfx_enabled:
        return
    if Options.auto_sfx:
        return
    effect = +Effect
    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            effect @= Effects.normal_hold
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            effect @= Effects.critical_hold
        case _:
            assert_never(kind)
    if replace:
        replace_looped_sfx(handle, effect)
    elif handle.id == 0:
        handle @= effect.loop()


def schedule_connector_sfx(
    kind: ActiveConnectorKind,
    timescale_group: int | EntityRef,
    start_time: float,
    end_time: float,
):
    if not Options.sfx_enabled:
        return
    effect = +Effect
    match kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            effect @= Effects.normal_hold
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            effect @= Effects.critical_hold
        case _:
            assert_never(kind)
    last_start_time = start_time
    hide = False
    for group in iter_timescale_changes_in_group_from_time(timescale_group, start_time):
        group_time = beat_to_time(group.beat)
        if group_time <= start_time:
            hide = group.hide_notes
            continue
        if group_time >= end_time:
            break
        if hide and not group.hide_notes:
            last_start_time = group_time
        elif not hide and group.hide_notes and group_time > last_start_time:
            schedule_looped_sfx(effect, last_start_time, group_time)
        hide = group.hide_notes
    if not hide and end_time > last_start_time:
        schedule_looped_sfx(effect, last_start_time, end_time)


def replace_looped_particle(handle: ParticleHandle, particle: Particle, layout: QuadLike, duration: float):
    if handle.id != 0:
        handle.destroy()
    handle @= particle.spawn(layout, duration / Options.effect_animation_speed, loop=True)


def update_looped_particle(handle: ParticleHandle, layout: QuadLike):
    if handle.id != 0:
        handle.move(layout)


def destroy_looped_particle(handle: ParticleHandle):
    if handle.id != 0:
        handle.destroy()
        handle.id = 0


def replace_looped_sfx(handle: LoopedEffectHandle, effect: Effect):
    if handle.id != 0:
        handle.stop()
    handle @= effect.loop()


def destroy_looped_sfx(handle: LoopedEffectHandle):
    if handle.id != 0:
        handle.stop()
        handle.id = 0


def schedule_looped_sfx(effect: Effect, start_time: float, end_time: float):
    effect.schedule_loop(start_time).stop(end_time)
