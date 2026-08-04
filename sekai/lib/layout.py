from __future__ import annotations

from enum import IntEnum
from math import atan, ceil, floor, log, pi

from sonolus.script.debug import static_error
from sonolus.script.globals import level_data, level_memory
from sonolus.script.interval import clamp, lerp, remap, unlerp
from sonolus.script.num import Num
from sonolus.script.quad import Quad, QuadLike, Rect
from sonolus.script.record import Record
from sonolus.script.runtime import aspect_ratio, background, is_play, is_watch, screen, set_background
from sonolus.script.vec import Vec2

from sekai.lib.options import Options
from sekai.lib.timescale import CompositeTime

LANE_T = 47 / 850
LANE_B = 1176 / 850

NOTE_H = 75 / 850 / 2
NOTE_EDGE_W = 0.25
NOTE_SLIM_EDGE_W = 0.125

TARGET_ASPECT_RATIO = 16 / 9

TEST_ASPECT_SCALE = 0.5

FIELD_T_FACTOR = 0.5 + 1.15875 * (47 / 1176)
FIELD_B_FACTOR = 0.5 - 1.15875 * (803 / 1176)
FIELD_W_FACTOR = (1.15875 * (1420 / 1176)) / TARGET_ASPECT_RATIO / 12

# Value between 0 and 1 where smaller values mean a 'harsher' approach with more acceleration.
APPROACH_SCALE = 1.07**-45

NOTE_REFERENCE_SCALE = 1.06**-45
NOTE_REFERENCE_TIME = 0.39
NOTE_SPEED_5_TO_12_RATIO = 8.75

STAGE_COVER_DEPTH_STEP = 0.009
HIDDEN_DEPTH_STEP = 0.01

VISIBILITY_LINE_HALF_HEIGHT = 0.001

# Value above 1 where we cut off drawing sprites. Doesn't really matter as long as it's high enough,
# such that something like a flick arrow below the judge line isn't obviously suddenly cut off.
DEFAULT_APPROACH_CUTOFF = 5

# Avoid numerical instability at low tilt in the approach curve
APPROACH_TILT_LERP_MIN = 0.05

# Stage width at 0 tilt
STAGE_WIDTH_MID = (APPROACH_SCALE + 1) / 2

# As tilt decreases, the perspective vanishing point (where the width factor reaches 0) recedes
# upward and the stage top is extended toward it. This floors the effective tilt used for that
# extent so it stays finite (instead of diverging) as tilt approaches 0.
STAGE_TILT_VANISH_MIN = 0.2

FLICK_ARROW_Y_OFFSET = 0.4


class FlickDirection(IntEnum):
    UP_OMNI = 0


@level_data
class Layout:
    field_w: float
    field_h: float
    approach_start: float
    cover_progress: float
    cutoff_progress: float
    flick_speed_threshold: float
    judgment_line_y_offset: float


@level_memory
class DynamicLayout:
    t: float
    w_scale: float
    h_scale: float
    x_translate: float
    rotate: float
    stage_tilt: float
    size_zoom: float
    note_h: float
    scaled_note_h: float
    progress_start: float
    progress_cutoff: float
    width_offset: float
    lane_t: float
    lane_b: float
    stage_lane_t: float
    stage_lane_b: float


class AffineTransform2d(Record):
    a00: float
    a01: float
    a02: float
    a10: float
    a11: float
    a12: float

    def apply(self, p: Vec2) -> Vec2:
        return Vec2(
            self.a00 * p.x + self.a01 * p.y + self.a02,
            self.a10 * p.x + self.a11 * p.y + self.a12,
        )

    def apply_inverse(self, p: Vec2) -> Vec2:
        det = self.a00 * self.a11 - self.a01 * self.a10
        dx = p.x - self.a02
        dy = p.y - self.a12
        return Vec2(
            (self.a11 * dx - self.a01 * dy) / det,
            (self.a00 * dy - self.a10 * dx) / det,
        )

    def transform_quad(self, q: QuadLike) -> Quad:
        return Quad(
            bl=self.apply(q.bl),
            br=self.apply(q.br),
            tl=self.apply(q.tl),
            tr=self.apply(q.tr),
        )


IDENTITY_AFFINE_TRANSFORM = AffineTransform2d(a00=1.0, a01=0.0, a02=0.0, a10=0.0, a11=1.0, a12=0.0)


def stage_aspect_ratio_locked() -> bool:
    return Options.lock_stage_aspect_ratio


def stage_cover_progress(value: float) -> float:
    if value <= 0:
        return 0.0
    depth = LANE_T + STAGE_COVER_DEPTH_STEP * value
    # Cancel the judgment-line shift that judgment_approach() applies at draw time, so the
    # boundary stays at this absolute depth regardless of the judgment line position.
    return inverse_approach_curve_base(depth) + Layout.judgment_line_y_offset


def hidden_progress(value: float) -> float:
    depth = max(1 - HIDDEN_DEPTH_STEP * value, APPROACH_SCALE)
    # Cancel the judgment-line shift, as in stage_cover_progress().
    return inverse_approach_curve_base(depth) + Layout.judgment_line_y_offset


def note_efold_time(note_speed: float) -> float:
    tau_12 = NOTE_REFERENCE_TIME / log(1 / NOTE_REFERENCE_SCALE)
    return tau_12 * NOTE_SPEED_5_TO_12_RATIO ** ((12 - clamp(note_speed, 1, 12)) / 7)


def configured_judgment_line_y_offset() -> float:
    depth = 1 - Options.judgment_line_position * HIDDEN_DEPTH_STEP / 2
    return 1 - inverse_approach_curve_base(depth)


def init_layout():
    if stage_aspect_ratio_locked():
        if aspect_ratio() > TARGET_ASPECT_RATIO:
            field_w = screen().h * TARGET_ASPECT_RATIO
            field_h = screen().h
        else:
            field_w = screen().w
            field_h = screen().w / TARGET_ASPECT_RATIO
    else:
        field_w = screen().w
        field_h = screen().h

    Layout.field_w = field_w
    Layout.field_h = field_h

    Layout.approach_start = 0.0
    Layout.judgment_line_y_offset = configured_judgment_line_y_offset()

    Layout.cover_progress = stage_cover_progress(Options.stage_cover)
    Layout.cutoff_progress = hidden_progress(Options.hidden) if Options.hidden else DEFAULT_APPROACH_CUTOFF

    refresh_layout()

    Layout.flick_speed_threshold = 2 * DynamicLayout.w_scale


def test_aspect_active() -> bool:
    return Options.test_aspect_ratio and (is_play() or is_watch())


def refresh_layout():
    base = base_layout_transform()
    DynamicLayout.t = base.t
    DynamicLayout.w_scale = base.w_scale
    DynamicLayout.h_scale = base.h_scale
    DynamicLayout.x_translate = base.x_translate
    DynamicLayout.rotate = base.rotate
    DynamicLayout.stage_tilt = base.stage_tilt
    DynamicLayout.size_zoom = base.size_zoom
    tilt = current_stage_tilt()

    DynamicLayout.width_offset = (1 - tilt) * STAGE_WIDTH_MID
    vanish_tilt = max(tilt, STAGE_TILT_VANISH_MIN)
    vanish_ext = (1 - vanish_tilt) * STAGE_WIDTH_MID / vanish_tilt
    DynamicLayout.lane_t = LANE_T - vanish_ext
    DynamicLayout.lane_b = LANE_B + vanish_ext
    DynamicLayout.stage_lane_t = LANE_T - vanish_ext
    DynamicLayout.stage_lane_b = LANE_B + vanish_ext

    base_note_h = NOTE_H * (0.6 * base.size_zoom + 0.4)
    flat_note_h = STAGE_WIDTH_MID * DynamicLayout.w_scale / (2 * abs(DynamicLayout.h_scale))
    DynamicLayout.note_h = lerp(flat_note_h, base_note_h, tilt)

    if test_aspect_active():
        DynamicLayout.t = DynamicLayout.t * TEST_ASPECT_SCALE
        DynamicLayout.w_scale = DynamicLayout.w_scale * TEST_ASPECT_SCALE
        DynamicLayout.h_scale = DynamicLayout.h_scale * TEST_ASPECT_SCALE
        DynamicLayout.x_translate = DynamicLayout.x_translate * TEST_ASPECT_SCALE
        set_background(background().scale(Vec2(TEST_ASPECT_SCALE, TEST_ASPECT_SCALE)))

    DynamicLayout.scaled_note_h = DynamicLayout.note_h * DynamicLayout.h_scale

    DynamicLayout.progress_start = Layout.cover_progress
    DynamicLayout.progress_cutoff = Layout.cutoff_progress


def current_stage_tilt() -> float:
    if is_play() or is_watch():
        return DynamicLayout.stage_tilt
    return 1.0


def approach_curve_base(x: float) -> float:
    if Options.alternative_approach_curve:
        d_0 = 1 / APPROACH_SCALE
        d_1 = 2.5
        v_1 = (d_0 - d_1) / d_1**2
        d = 1 / lerp(d_0, d_1, x) if x < 1 else 1 / d_1 + v_1 * (x - 1)
        return remap(1 / d_0, 1 / d_1, APPROACH_SCALE, 1, d)
    return APPROACH_SCALE ** (1 - x)


def inverse_approach_curve_base(approach_value: float) -> float:
    if Options.alternative_approach_curve:
        d_0 = 1 / APPROACH_SCALE
        d_1 = 2.5
        v_1 = (d_0 - d_1) / d_1**2
        d = remap(APPROACH_SCALE, 1, 1 / d_0, 1 / d_1, approach_value)
        if d <= 1 / d_1:
            raw = (1 / d - d_0) / (d_1 - d_0)
        else:
            raw = 1 + (d - 1 / d_1) / v_1
    else:
        raw = 1 - log(approach_value) / log(APPROACH_SCALE)
    return raw


def approach_slice_window(tilt: float, spawn_depth: float) -> tuple[float, float]:
    w_judge = width_factor_at_tilt(1.0, tilt)
    spawn_fraction = tilt * (1.0 - spawn_depth) / w_judge
    slice_spawn = 1.0 - spawn_fraction
    return inverse_approach_curve_base(slice_spawn), slice_spawn


def approach_slice(progress: float, tilt: float, spawn_depth: float) -> float:
    start, slice_spawn = approach_slice_window(tilt, spawn_depth)
    travel = approach_curve_base(lerp(start, 1.0, progress))
    return remap(slice_spawn, 1.0, spawn_depth, 1.0, travel)


def inverse_approach_slice(travel: float, tilt: float, spawn_depth: float) -> float:
    start, slice_spawn = approach_slice_window(tilt, spawn_depth)
    raw = remap(spawn_depth, 1.0, slice_spawn, 1.0, travel)
    return unlerp(start, 1.0, inverse_approach_curve_base(raw))


def approach_at_tilt(progress: float, tilt: float) -> float:
    if tilt >= 1.0:
        return approach_curve_base(lerp(Layout.approach_start, 1.0, progress))
    spawn_depth = approach_curve_base(Layout.approach_start)
    if tilt <= 0.0:
        return lerp(spawn_depth, 1.0, progress)
    if tilt < APPROACH_TILT_LERP_MIN:
        linear = lerp(spawn_depth, 1.0, progress)
        slice_at_floor = approach_slice(progress, APPROACH_TILT_LERP_MIN, spawn_depth)
        return lerp(linear, slice_at_floor, tilt / APPROACH_TILT_LERP_MIN)
    return approach_slice(progress, tilt, spawn_depth)


def approach(progress: float) -> float:
    return approach_at_tilt(progress, current_stage_tilt())


def judgment_approach_at_tilt(progress: float, tilt: float, y_offset: float = 0.0) -> float:
    return approach_at_tilt(progress - y_offset - Layout.judgment_line_y_offset, tilt)


def judgment_approach(progress: float, y_offset: float = 0.0) -> float:
    return judgment_approach_at_tilt(progress, current_stage_tilt(), y_offset)


def judgment_progress_at_travel(travel: float, y_offset: float = 0.0) -> float:
    return inverse_approach_tilt(travel) + y_offset + Layout.judgment_line_y_offset


def inverse_approach_untilted(approach_value: float) -> float:
    return unlerp(Layout.approach_start, 1.0, inverse_approach_curve_base(approach_value))


def inverse_approach_tilt(approach_value: float) -> float:
    tilt = current_stage_tilt()
    if tilt >= 1.0:
        return inverse_approach_untilted(approach_value)
    spawn_depth = approach_curve_base(Layout.approach_start)
    if tilt < APPROACH_TILT_LERP_MIN:
        lo = -8.0
        hi = 8.0
        for _ in range(20):
            mid = (lo + hi) / 2
            too_low = approach_at_tilt(mid, tilt) < approach_value
            lo = mid if too_low else lo
            hi = hi if too_low else mid
        return (lo + hi) / 2
    return inverse_approach_slice(approach_value, tilt, spawn_depth)


def progress_to(
    to_time: float | CompositeTime,
    now: float | CompositeTime,
    preempt: float,
) -> float:
    match (to_time, now):
        case (CompositeTime(), CompositeTime()):
            return ((now.base - to_time.base) + now.delta - to_time.delta + preempt) / preempt
        case (Num(), Num()):
            return unlerp(to_time - preempt, to_time, now)
        case _:
            static_error("Unexpected types for progress_to")


def preempt_time(force_speed: float = 0) -> float:
    note_speed = force_speed if force_speed > 0 else Options.note_speed
    return note_efold_time(note_speed) * log(1 / APPROACH_SCALE)


def get_alpha(target_time: float, now: float | None = None) -> float:
    return 1.0


def width_factor_at_tilt(depth: float, tilt: float) -> float:
    return tilt * depth + (1 - tilt) * STAGE_WIDTH_MID


def tilt_width_factor(depth: float) -> float:
    return current_stage_tilt() * depth + DynamicLayout.width_offset


def tilt_depth(line_y: float, travel: float) -> float:
    return travel + (line_y - 1.0) * lerp(1.0, travel, current_stage_tilt())


def tilt_widened_edge(bottom_edge: float, top_edge: float) -> float:
    return lerp(bottom_edge, top_edge, current_stage_tilt())


def transform_vec(v: Vec2) -> Vec2:
    return Vec2(
        v.x * DynamicLayout.w_scale + DynamicLayout.x_translate,
        v.y * DynamicLayout.h_scale + DynamicLayout.t,
    ).rotate(-DynamicLayout.rotate)


def transform_quad(q: QuadLike) -> Quad:
    return Quad(
        bl=transform_vec(q.bl),
        br=transform_vec(q.br),
        tl=transform_vec(q.tl),
        tr=transform_vec(q.tr),
    )


def transformed_vec_at(lane: float, travel: float = 1.0) -> Vec2:
    return transform_vec(Vec2(lane * tilt_width_factor(travel), travel))


def pre_rotation_vec_at(lane: float, travel: float = 1.0) -> Vec2:
    return Vec2(
        lane * tilt_width_factor(travel) * DynamicLayout.w_scale + DynamicLayout.x_translate,
        travel * DynamicLayout.h_scale + DynamicLayout.t,
    )


def touch_to_lane(pos: Vec2, transform: AffineTransform2d) -> float:
    unrotated = transform.apply_inverse(pos).rotate(DynamicLayout.rotate)
    y_raw = (unrotated.y - DynamicLayout.t) / DynamicLayout.h_scale
    x_raw = (unrotated.x - DynamicLayout.x_translate) / DynamicLayout.w_scale
    width = tilt_width_factor(y_raw)
    if -1e-6 < width < 1e-6:
        width = 1e-6 if width >= 0 else -1e-6
    return x_raw / width


def perspective_vec(x: float, y: float, travel: float = 1.0) -> Vec2:
    return transform_vec(Vec2(x * tilt_width_factor(y * travel), y * travel))


def perspective_rect(l: float, r: float, t: float, b: float, travel: float = 1.0) -> Quad:
    depth_b = tilt_depth(b, travel)
    depth_t = tilt_depth(t, travel)
    wb = tilt_width_factor(depth_b)
    wt = tilt_width_factor(depth_t)
    return transform_quad(
        Quad(
            bl=Vec2(l * wb, depth_b),
            br=Vec2(r * wb, depth_b),
            tl=Vec2(l * wt, depth_t),
            tr=Vec2(r * wt, depth_t),
        )
    )


def layout_holodori_stage() -> Quad:
    w = (2048 / 1420) * 12 / 2
    h = 1176 / 850
    rect = Rect(l=-w, r=w, t=LANE_T, b=LANE_T + h)
    return transform_quad(rect)


def layout_stage_lane_by_edges(l: float, r: float, y_offset: float = 0.0) -> Quad:
    return perspective_rect(
        l=l, r=r, t=DynamicLayout.stage_lane_t, b=DynamicLayout.stage_lane_b, travel=approach(1 - y_offset)
    )


def layout_particle_lane(lane: float, size: float, y_offset: float = 0.0) -> Quad:
    return perspective_rect(
        l=lane - size,
        r=lane + size,
        t=DynamicLayout.lane_t,
        b=DynamicLayout.lane_b,
        travel=judgment_approach(1, y_offset),
    )


def layout_fallback_judge_line(travel: float = 1.0) -> Quad:
    nh = DynamicLayout.note_h
    return perspective_rect(l=-6, r=6, t=1 - nh, b=1 + nh, travel=travel)


def layout_note_body_by_edges(l: float, r: float, h: float, travel: float):
    return perspective_rect(l=l, r=r, t=1 - h, b=1 + h, travel=travel)


def layout_note_body_slices_by_edges(
    l: float, r: float, h: float, edge_w: float, travel: float
) -> tuple[Quad, Quad, Quad]:
    m = (l + r) / 2
    if r < l:
        # Make the note 0 width; shouldn't normally happen, but in case, we want to handle it gracefully
        l = r = m
    ml = min(l + edge_w, m)
    mr = max(r - edge_w, m)
    return (
        layout_note_body_by_edges(l=l, r=ml, h=h, travel=travel),
        layout_note_body_by_edges(l=ml, r=mr, h=h, travel=travel),
        layout_note_body_by_edges(l=mr, r=r, h=h, travel=travel),
    )


def layout_regular_note_body(lane: float, size: float, travel: float) -> tuple[Quad, Quad, Quad]:
    return layout_note_body_slices_by_edges(
        l=lane - size + Options.note_margin,
        r=lane + size - Options.note_margin,
        h=DynamicLayout.note_h,
        edge_w=NOTE_EDGE_W,
        travel=travel,
    )


def layout_regular_note_body_fallback(lane: float, size: float, travel: float) -> Quad:
    return layout_note_body_by_edges(
        l=lane - size + Options.note_margin,
        r=lane + size - Options.note_margin,
        h=DynamicLayout.note_h,
        travel=travel,
    )


def layout_slim_note_body(lane: float, size: float, travel: float) -> tuple[Quad, Quad, Quad]:
    return layout_note_body_slices_by_edges(
        l=lane - size + Options.note_margin,
        r=lane + size - Options.note_margin,
        h=DynamicLayout.note_h,  # Height is handled by the sprite rather than being changed here
        edge_w=NOTE_SLIM_EDGE_W,
        travel=travel,
    )


def layout_slim_note_body_fallback(lane: float, size: float, travel: float) -> Quad:
    return layout_note_body_by_edges(
        l=lane - size + Options.note_margin,
        r=lane + size - Options.note_margin,
        h=DynamicLayout.note_h / 2,  # For fallback, we need to halve the height manually engine-side
        travel=travel,
    )


def layout_tick(lane: float, travel: float) -> Quad:
    center = transformed_vec_at(lane, travel)
    h = -DynamicLayout.scaled_note_h * tilt_width_factor(travel)
    rot = -DynamicLayout.rotate
    dx = Vec2(h, 0).rotate(rot)
    dy = Vec2(0, h).rotate(rot)
    return Quad(
        bl=center - dx - dy,
        tl=center - dx + dy,
        tr=center + dx + dy,
        br=center + dx - dy,
    )


def layout_note_icon(lane: float, travel: float) -> Quad:
    half_width = abs(DynamicLayout.scaled_note_h / DynamicLayout.w_scale)
    return perspective_rect(
        l=lane - half_width,
        r=lane + half_width,
        t=1 - DynamicLayout.note_h,
        b=1 + DynamicLayout.note_h,
        travel=travel,
    )


def layout_flick_arrow(lane: float, size: float, travel: float) -> Quad:
    w = clamp(size, 0, 3) / 2
    base_bl = transformed_vec_at(lane - w, travel)
    base_br = transformed_vec_at(lane + w, travel)
    up = (base_br - base_bl).rotate(pi / 2)
    base_tl = base_bl + up
    base_tr = base_br + up
    offset = Vec2(0, FLICK_ARROW_Y_OFFSET * DynamicLayout.w_scale).rotate(-DynamicLayout.rotate) * tilt_width_factor(
        travel
    )
    return Quad(
        bl=base_bl,
        br=base_br,
        tl=base_tl,
        tr=base_tr,
    ).translate(offset)


def layout_flick_arrow_fallback(lane: float, size: float, travel: float) -> Quad:
    w = clamp(size / 2, 1, 2)
    width = tilt_width_factor(travel)
    offset = Vec2(0, FLICK_ARROW_Y_OFFSET * DynamicLayout.w_scale) * width
    return (
        Rect(l=-1, r=1, t=1, b=-1)
        .as_quad()
        .scale(Vec2(w, w) * DynamicLayout.w_scale * width)
        .translate(offset)
        .rotate(-DynamicLayout.rotate)
        .translate(transformed_vec_at(lane, travel))
    )


def layout_slot_effect(lane: float, y_offset: float = 0.0) -> Quad:
    travel = judgment_approach(1, y_offset)
    nh = DynamicLayout.note_h
    return perspective_rect(
        l=lane - 0.5,
        r=lane + 0.5,
        b=1 + nh,
        t=1 - nh,
        travel=travel,
    )


def layout_slot_glow_effect(lane: float, size: float, height: float, y_offset: float = 0.0) -> Quad:
    s = 1 + 0.25 * Options.slot_effect_size
    travel = judgment_approach(1, y_offset)
    h = 4.25 * DynamicLayout.w_scale * Options.slot_effect_size * tilt_width_factor(travel)
    up = Vec2(0, h).rotate(-DynamicLayout.rotate)
    l_min = transformed_vec_at(lane - size, travel)
    r_min = transformed_vec_at(lane + size, travel)
    l_max = transformed_vec_at((lane - size) * s, travel) + up
    r_max = transformed_vec_at((lane + size) * s, travel) + up
    return Quad(
        bl=l_min,
        br=r_min,
        tl=lerp(l_min, l_max, height),
        tr=lerp(r_min, r_max, height),
    )


def layout_linear_effect(lane: float, shear: float, y_offset: float = 0.0) -> Quad:
    w = Options.note_effect_size
    travel = judgment_approach(1, y_offset)
    bl = transformed_vec_at(lane - w, travel)
    br = transformed_vec_at(lane + w, travel)
    up = (br - bl).rotate(pi / 2) + (shear + 0.125 * lane) * (br - bl) / 2
    return Quad(
        bl=bl,
        br=br,
        tl=bl + up,
        tr=br + up,
    )


def layout_rotated_linear_effect(lane: float, shear: float, y_offset: float = 0.0) -> Quad:
    w = Options.note_effect_size
    travel = judgment_approach(1, y_offset)
    bl = transformed_vec_at(lane - w, travel)
    br = transformed_vec_at(lane + w, travel)
    up = (br - bl).orthogonal()
    return Quad(
        bl=bl,
        br=br,
        tl=bl + up,
        tr=br + up,
    ).rotate_about(atan(-(shear + 0.125 * lane) / 2), pivot=(bl + br) / 2)


def layout_circular_effect(lane: float, w: float, h: float, y_offset: float = 0.0) -> Quad:
    travel = judgment_approach(1, y_offset)
    width = tilt_width_factor(travel)
    w *= Options.note_effect_size * width
    h *= Options.note_effect_size * DynamicLayout.w_scale / DynamicLayout.h_scale
    t = travel + h * width
    b = travel - h * width
    wb = tilt_width_factor(b)
    wt = tilt_width_factor(t)
    return transform_quad(
        Quad(
            bl=Vec2(lane * wb - w, b),
            br=Vec2(lane * wb + w, b),
            tl=Vec2(lane * wt - w, t),
            tr=Vec2(lane * wt + w, t),
        )
    )


def layout_tick_effect(lane: float, y_offset: float = 0.0) -> Quad:
    travel = judgment_approach(1, y_offset)
    w = 4 * DynamicLayout.w_scale * Options.note_effect_size * tilt_width_factor(travel)
    center = transformed_vec_at(lane, travel)
    rot = -DynamicLayout.rotate
    dx = Vec2(w, 0).rotate(rot)
    dy = Vec2(0, w).rotate(rot)
    return Quad(
        bl=center - dx - dy,
        tl=center - dx + dy,
        tr=center + dx + dy,
        br=center + dx - dy,
    )


def layout_slide_connector_segment(
    start_lane: float,
    start_size: float,
    start_travel: float,
    end_lane: float,
    end_size: float,
    end_travel: float,
) -> Quad:
    if start_travel < end_travel:
        start_lane, end_lane = end_lane, start_lane
        start_size, end_size = end_size, start_size
        start_travel, end_travel = end_travel, start_travel
    return Quad(
        bl=perspective_vec(start_lane - start_size, 1, start_travel),
        br=perspective_vec(start_lane + start_size, 1, start_travel),
        tl=perspective_vec(end_lane - end_size, 1, end_travel),
        tr=perspective_vec(end_lane + end_size, 1, end_travel),
    )


def st_slide_connector_segment(
    start_lane: float,
    start_size: float,
    start_travel: float,
    end_lane: float,
    end_size: float,
    end_travel: float,
    start_transform: AffineTransform2d,
    end_transform: AffineTransform2d,
) -> Quad:
    result = +Quad
    if start_travel >= end_travel:
        result @= Quad(
            bl=start_transform.apply(perspective_vec(start_lane - start_size, 1, start_travel)),
            br=start_transform.apply(perspective_vec(start_lane + start_size, 1, start_travel)),
            tl=end_transform.apply(perspective_vec(end_lane - end_size, 1, end_travel)),
            tr=end_transform.apply(perspective_vec(end_lane + end_size, 1, end_travel)),
        )
    else:
        result @= Quad(
            bl=end_transform.apply(perspective_vec(end_lane - end_size, 1, end_travel)),
            br=end_transform.apply(perspective_vec(end_lane + end_size, 1, end_travel)),
            tl=start_transform.apply(perspective_vec(start_lane - start_size, 1, start_travel)),
            tr=start_transform.apply(perspective_vec(start_lane + start_size, 1, start_travel)),
        )
    return result


def layout_sim_line(
    left_lane: float,
    left_travel: float,
    right_lane: float,
    right_travel: float,
    left_transform: AffineTransform2d,
    right_transform: AffineTransform2d,
) -> Quad:
    ml = +Vec2
    mr = +Vec2
    if left_lane <= right_lane:
        ml @= left_transform.apply(perspective_vec(left_lane, 1, left_travel))
        mr @= right_transform.apply(perspective_vec(right_lane, 1, right_travel))
        ml_travel = left_travel
        mr_travel = right_travel
    else:
        ml @= right_transform.apply(perspective_vec(right_lane, 1, right_travel))
        mr @= left_transform.apply(perspective_vec(left_lane, 1, left_travel))
        ml_travel = right_travel
        mr_travel = left_travel
    ort = (mr - ml).orthogonal().normalize_or_zero()
    ml_h = DynamicLayout.scaled_note_h * tilt_width_factor(ml_travel)
    mr_h = DynamicLayout.scaled_note_h * tilt_width_factor(mr_travel)
    return Quad(
        bl=ml + ort * ml_h,
        br=mr + ort * mr_h,
        tl=ml - ort * ml_h,
        tr=mr - ort * mr_h,
    )


def layout_perspective_line(l: float, r: float, travel: float, half_height: float) -> Quad:
    depth_t = travel - half_height
    depth_b = travel + half_height
    return transform_quad(
        Quad(
            bl=Vec2(l * tilt_width_factor(depth_b), depth_b),
            br=Vec2(r * tilt_width_factor(depth_b), depth_b),
            tl=Vec2(l * tilt_width_factor(depth_t), depth_t),
            tr=Vec2(r * tilt_width_factor(depth_t), depth_t),
        )
    )


def layout_visibility_line(progress: float) -> Quad:
    return layout_perspective_line(-6.5, 6.5, judgment_approach(progress), VISIBILITY_LINE_HALF_HEIGHT)


class HitboxTarget(Record):
    l: Vec2
    r: Vec2


class Hitbox(Record):
    target: HitboxTarget
    bounds: Quad


class LayoutTransform(Record):
    t: float
    w_scale: float
    h_scale: float
    x_translate: float
    rotate: float
    stage_tilt: float
    size_zoom: float


def current_layout_transform() -> LayoutTransform:
    return LayoutTransform(
        t=DynamicLayout.t,
        w_scale=DynamicLayout.w_scale,
        h_scale=DynamicLayout.h_scale,
        x_translate=DynamicLayout.x_translate,
        rotate=DynamicLayout.rotate,
        stage_tilt=DynamicLayout.stage_tilt,
        size_zoom=DynamicLayout.size_zoom,
    )


def base_layout_transform() -> LayoutTransform:
    t = Layout.field_h * FIELD_T_FACTOR
    w = Layout.field_w * FIELD_W_FACTOR
    return LayoutTransform(
        t=t,
        w_scale=w,
        h_scale=Layout.field_h * FIELD_B_FACTOR - t,
        x_translate=0.0,
        rotate=0.0,
        stage_tilt=1.0,
        size_zoom=1.0,
    )


def apply_test_aspect(transform: LayoutTransform) -> LayoutTransform:
    result = +LayoutTransform
    if test_aspect_active():
        result @= LayoutTransform(
            t=transform.t * TEST_ASPECT_SCALE,
            w_scale=transform.w_scale * TEST_ASPECT_SCALE,
            h_scale=transform.h_scale * TEST_ASPECT_SCALE,
            x_translate=transform.x_translate * TEST_ASPECT_SCALE,
            rotate=transform.rotate,
            stage_tilt=transform.stage_tilt,
            size_zoom=transform.size_zoom,
        )
    else:
        result @= transform
    return result


def static_layout_transform() -> LayoutTransform:
    return apply_test_aspect(base_layout_transform())


def compute_hitbox(
    transform: LayoutTransform,
    lane: float,
    size: float,
    leniency: float,
    y_offset: float = 0.0,
) -> Hitbox:
    tilt = transform.stage_tilt
    travel = judgment_approach_at_tilt(1, tilt, y_offset)
    width_factor = width_factor_at_tilt(travel, tilt)
    l_x = (lane - size) * width_factor * transform.w_scale + transform.x_translate
    r_x = (lane + size) * width_factor * transform.w_scale + transform.x_translate
    note_y = travel * transform.h_scale + transform.t
    # We intentionally don't adjust for tilt to give the same screen-space leniency at low tilt
    lane_w = transform.w_scale
    # Dividing out size_zoom keeps the vertical extent constant in screen space regardless of camera size
    vertical_lane_w = lane_w / transform.size_zoom
    vertical_half_lanes = 5.0
    vertical_extent = vertical_half_lanes * vertical_lane_w
    rot = -transform.rotate
    bl_x = l_x - leniency * lane_w
    br_x = r_x + leniency * lane_w
    b_y = note_y - vertical_extent
    t_y = note_y + vertical_extent
    target_l = Vec2(l_x, note_y).rotate(rot)
    target_r = Vec2(r_x, note_y).rotate(rot)
    bound_bl = Vec2(bl_x, b_y).rotate(rot)
    bound_br = Vec2(br_x, b_y).rotate(rot)
    bound_tl = Vec2(bl_x, t_y).rotate(rot)
    bound_tr = Vec2(br_x, t_y).rotate(rot)
    return Hitbox(
        target=HitboxTarget(l=target_l, r=target_r),
        bounds=Quad(bl=bound_bl, br=bound_br, tl=bound_tl, tr=bound_tr),
    )


def segment_closeness_score(p: Vec2, seg: HitboxTarget) -> float:
    d = seg.r - seg.l
    t = clamp((p - seg.l).dot(d) / d.dot(d), 0.0, 1.0)
    return -(p - (seg.l + d * t)).magnitude


def layout_lane_area(l: float, r: float) -> Quad:
    return perspective_rect(l, r, LANE_T, LANE_B)


def iter_slot_lanes(lane: float, size: float, pivot_lane: float = 0.0, half_offset: bool = False):
    e = 1e-6
    offset = 0.0 if half_offset else 0.5
    shift = pivot_lane + offset - 0.5
    shifted_lane = lane - shift
    for i in range(floor(shifted_lane - size + e), ceil(shifted_lane + size - e)):
        yield i + 0.5 + shift
