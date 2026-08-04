from __future__ import annotations

from enum import IntEnum
from math import ceil, floor
from typing import assert_never

from sonolus.script.interval import clamp, lerp
from sonolus.script.quad import Quad, QuadLike, Rect
from sonolus.script.record import Record
from sonolus.script.sprite import Sprite
from sonolus.script.vec import Vec2

from sekai.lib.effect import SFX_DISTANCE, Effects
from sekai.lib.layer import LAYER_COVER, LAYER_OVERLAY, LAYER_STAGE, ZIndexes, get_z, get_z_alt
from sekai.lib.layout import (
    IDENTITY_AFFINE_TRANSFORM,
    TEST_ASPECT_SCALE,
    AffineTransform2d,
    DynamicLayout,
    Layout,
    current_stage_tilt,
    judgment_approach,
    layout_fallback_judge_line,
    layout_holodori_stage,
    layout_particle_lane,
    layout_stage_lane_by_edges,
    layout_visibility_line,
    perspective_rect,
    stage_aspect_ratio_locked,
    tilt_depth,
    tilt_widened_edge,
    tilt_width_factor,
    transformed_vec_at,
)
from sekai.lib.options import Options
from sekai.lib.particle import ActiveParticles
from sekai.lib.skin import ActiveSkin, JudgmentSpriteSet


class JudgeLineColor(IntEnum):
    NEUTRAL = 0
    RED = 1
    GREEN = 2
    BLUE = 3
    YELLOW = 4
    PURPLE = 5
    CYAN = 6
    BLACK = 7


class DivisionParity(IntEnum):
    EVEN = 0
    ODD = 1


class DivisionProps(Record):
    size: int
    parity: DivisionParity


class StageBorderStyle(IntEnum):
    DEFAULT = 0
    LIGHT = 1
    DISABLED = 2
    MEDIUM = 3


class JudgeLineStyle(IntEnum):
    DEFAULT = 0
    SINGLE_LINE = 1


FULL_WIDTH_HALF_EXTENT = 48.0
JUDGE_LINE_BORDER_FACTOR = 5.0


def full_width_factor(full_width: bool) -> float:
    return 1.0 if full_width else 0.0


class Transition[T](Record):
    start: T
    end: T
    progress: float


def judge_line_style_weight(style: Transition[JudgeLineStyle], target: JudgeLineStyle) -> float:
    weight = 0.0
    if style.start == target:
        weight += 1 - style.progress
    if style.end == target:
        weight += style.progress
    return weight


def resolve_judge_line_style(style: Transition[JudgeLineStyle]) -> JudgeLineStyle:
    """The dominant judge line style at the current moment, for discrete decisions (e.g. slot effects)."""
    if style.progress < 0.5:
        return style.start
    return style.end


TEST_ASPECT_BOX_EDGE = 0.004


def draw_aspect_box(sprite: Sprite, ratio: float, sub: int):
    if not stage_aspect_ratio_locked():
        return
    hf = TEST_ASPECT_SCALE * Layout.field_h / 2
    wf = TEST_ASPECT_SCALE * Layout.field_w / 2
    if ratio < wf / hf:
        hw = wf
        hh = wf / ratio
    else:
        hw = ratio * hf
        hh = hf
    e = TEST_ASPECT_BOX_EDGE
    top = Rect(l=-hw - e, r=hw + e, t=hh + e, b=hh - e)
    bottom = Rect(l=-hw - e, r=hw + e, t=-hh + e, b=-hh - e)
    left = Rect(l=-hw - e, r=-hw + e, t=hh, b=-hh)
    right = Rect(l=hw - e, r=hw + e, t=hh, b=-hh)
    sprite.draw(top.as_quad(), z=get_z_alt(LAYER_OVERLAY, 1000 + 4 * sub).tuple, a=1.0)
    sprite.draw(bottom.as_quad(), z=get_z_alt(LAYER_OVERLAY, 1000 + 4 * sub + 1).tuple, a=1.0)
    sprite.draw(left.as_quad(), z=get_z_alt(LAYER_OVERLAY, 1000 + 4 * sub + 2).tuple, a=1.0)
    sprite.draw(right.as_quad(), z=get_z_alt(LAYER_OVERLAY, 1000 + 4 * sub + 3).tuple, a=1.0)


def draw_test_aspect_overlay():
    if not Options.test_aspect_ratio:
        return
    # Higher sub = drawn on top; 16:9 (the field reference) is drawn last so it sits topmost.
    draw_aspect_box(ActiveSkin.guide_red, 21 / 9, 0)
    draw_aspect_box(ActiveSkin.guide_blue, 4 / 3, 1)
    draw_aspect_box(ActiveSkin.guide_green, 16 / 9, 2)


def draw_stage_and_accessories():
    draw_basic_stage()
    draw_stage_cover()
    draw_test_aspect_overlay()


def normalize_transition[T](value: Transition[T] | T) -> Transition[T]:
    if isinstance(value, Transition):
        return value
    return Transition(start=value, end=value, progress=0)


def draw_basic_stage():
    if not Options.show_lane:
        return
    if ActiveSkin.holodori_stage.is_available:
        draw_holodori_stage()
    else:
        draw_default_stage(
            lane=0,
            width=6,
            pivot_lane=0,
            division=DivisionProps(size=2, parity=DivisionParity.EVEN),
            judge_line_color=JudgeLineColor.PURPLE,
            left_border_style=StageBorderStyle.DEFAULT,
            right_border_style=StageBorderStyle.DEFAULT,
            order=0,
            transform=IDENTITY_AFFINE_TRANSFORM,
        )


def draw_holodori_stage():
    stage_layout = layout_holodori_stage()
    judgment_line_layout = layout_fallback_judge_line(judgment_approach(1))
    ActiveSkin.holodori_stage_background.draw(
        stage_layout, z=get_z_alt(LAYER_STAGE, 0).tuple, a=1 - (Options.stage_brightness / 100)
    )
    ActiveSkin.holodori_stage.draw(stage_layout, z=get_z_alt(LAYER_STAGE, 1).tuple)
    ActiveSkin.holodori_stage_judgment_line.draw(judgment_line_layout, z=get_z_alt(LAYER_STAGE, 2).tuple)


def get_judgment_sprites(judge_line_color: JudgeLineColor) -> JudgmentSpriteSet:
    result = +JudgmentSpriteSet
    match judge_line_color:
        case JudgeLineColor.NEUTRAL:
            result @= ActiveSkin.judgment_neutral
        case JudgeLineColor.RED:
            result @= ActiveSkin.judgment_red
        case JudgeLineColor.GREEN:
            result @= ActiveSkin.judgment_green
        case JudgeLineColor.BLUE:
            result @= ActiveSkin.judgment_blue
        case JudgeLineColor.YELLOW:
            result @= ActiveSkin.judgment_yellow
        case JudgeLineColor.PURPLE:
            result @= ActiveSkin.judgment_purple
        case JudgeLineColor.CYAN:
            result @= ActiveSkin.judgment_cyan
        case JudgeLineColor.BLACK:
            result @= ActiveSkin.judgment_black
        case _:
            assert_never(judge_line_color)
    return result


def draw_default_stage(
    lane: float,
    width: float,
    pivot_lane: float,
    division: Transition[DivisionProps] | DivisionProps,
    judge_line_color: Transition[JudgeLineColor] | JudgeLineColor,
    left_border_style: Transition[StageBorderStyle] | StageBorderStyle,
    right_border_style: Transition[StageBorderStyle] | StageBorderStyle,
    order: int,
    lane_alpha: float = 1,
    judge_line_alpha: float = 1,
    y_offset: float = 0,
    judge_line_style: Transition[JudgeLineStyle] | JudgeLineStyle = JudgeLineStyle.DEFAULT,
    full_width: float = 0,
    division_line_alpha: float = 1,
    *,
    transform: AffineTransform2d,
):
    division = normalize_transition(division)
    judge_line_color = normalize_transition(judge_line_color)
    judge_line_style = normalize_transition(judge_line_style)
    left_border_style = normalize_transition(left_border_style)
    right_border_style = normalize_transition(right_border_style)

    def place(q: QuadLike) -> QuadLike:
        return transform.transform_quad(q)

    sprites_same = judge_line_color.start == judge_line_color.end
    sprites_a = get_judgment_sprites(judge_line_color.start)
    sprites_b = get_judgment_sprites(judge_line_color.end)
    p_sprites = judge_line_color.progress

    w_default = judge_line_style_weight(judge_line_style, JudgeLineStyle.DEFAULT)
    w_single_line = judge_line_style_weight(judge_line_style, JudgeLineStyle.SINGLE_LINE)
    fw = clamp(full_width, 0, 1)

    if not ActiveSkin.lane_background.is_available:
        draw_fallback_stage(
            lane,
            width,
            division.end.size,
            division.end.parity,
            pivot_lane,
            order,
            lane_alpha,
            judge_line_alpha,
            y_offset,
            judge_line_style,
            fw,
            transform=transform,
        )
        return

    travel = judgment_approach(1, y_offset)
    nh = DynamicLayout.note_h
    l = lane - width
    r = lane + width
    half_jl = lerp(width, FULL_WIDTH_HALF_EXTENT, fw)
    l_jl = lane - half_jl
    r_jl = lane + half_jl
    z_bg0 = get_z_alt(LAYER_STAGE, order * 17)
    z_bg1_a = get_z_alt(LAYER_STAGE, order * 17 + 1)
    z_bg1_b = get_z_alt(LAYER_STAGE, order * 17 + 2)
    z_lane0 = get_z_alt(LAYER_STAGE, order * 17 + 3)
    z_lane1 = get_z_alt(LAYER_STAGE, order * 17 + 4)
    z_a0 = get_z_alt(LAYER_STAGE, order * 17 + 5)
    z_a1 = get_z_alt(LAYER_STAGE, order * 17 + 6)
    z_a2 = get_z_alt(LAYER_STAGE, order * 17 + 7)
    z_a3 = get_z_alt(LAYER_STAGE, order * 17 + 8)
    z_b0 = get_z_alt(LAYER_STAGE, order * 17 + 9)
    z_b1 = get_z_alt(LAYER_STAGE, order * 17 + 10)
    z_b2 = get_z_alt(LAYER_STAGE, order * 17 + 11)
    z_b3 = get_z_alt(LAYER_STAGE, order * 17 + 12)
    z_a4 = get_z_alt(LAYER_STAGE, order * 17 + 13)
    z_b4 = get_z_alt(LAYER_STAGE, order * 17 + 14)
    z_single_a = get_z_alt(LAYER_STAGE, order * 17 + 15)
    z_single_b = get_z_alt(LAYER_STAGE, order * 17 + 16)

    f = JUDGE_LINE_BORDER_FACTOR

    def draw_left_border(style: StageBorderStyle, z: ZIndexes, a: float):
        match style:
            case StageBorderStyle.DEFAULT | StageBorderStyle.MEDIUM:
                scale = 0.5 if style == StageBorderStyle.MEDIUM else 1.0
                layout_b = layout_stage_lane_by_edges(
                    l - 0.08 * scale, l
                )  # Artificially thicken the top so it renders better
                layout_t = layout_stage_lane_by_edges(tilt_widened_edge(l - 0.08 * scale, l - 0.64 * scale), l)
                ActiveSkin.stage_border.draw(
                    place(Quad(bl=layout_b.bl, tl=layout_t.tl, tr=layout_t.tr, br=layout_b.br)), z=z.tuple, a=a
                )
            case StageBorderStyle.LIGHT:
                layout_b = layout_stage_lane_by_edges(l - 0.0125, l + 0.0125)
                layout_t = layout_stage_lane_by_edges(
                    tilt_widened_edge(l - 0.0125, l - 0.1), tilt_widened_edge(l + 0.0125, l + 0.1)
                )
                ActiveSkin.lane_divider.draw(
                    place(Quad(bl=layout_b.bl, tl=layout_t.tl, tr=layout_t.tr, br=layout_b.br)), z=z.tuple, a=a
                )
            case StageBorderStyle.DISABLED:
                pass
            case _:
                assert_never(style)

    def draw_right_border(style: StageBorderStyle, z: ZIndexes, a: float):
        match style:
            case StageBorderStyle.DEFAULT | StageBorderStyle.MEDIUM:
                scale = 0.5 if style == StageBorderStyle.MEDIUM else 1.0
                layout_b = layout_stage_lane_by_edges(r + 0.08 * scale, r)  # Flip horizontally
                layout_t = layout_stage_lane_by_edges(tilt_widened_edge(r + 0.08 * scale, r + 0.64 * scale), r)
                ActiveSkin.stage_border.draw(
                    place(Quad(bl=layout_b.bl, tl=layout_t.tl, tr=layout_t.tr, br=layout_b.br)), z=z.tuple, a=a
                )
            case StageBorderStyle.LIGHT:
                layout_b = layout_stage_lane_by_edges(r - 0.0125, r + 0.0125)
                layout_t = layout_stage_lane_by_edges(
                    tilt_widened_edge(r - 0.0125, r - 0.1), tilt_widened_edge(r + 0.0125, r + 0.1)
                )
                ActiveSkin.lane_divider.draw(
                    place(Quad(bl=layout_b.bl, tl=layout_t.tl, tr=layout_t.tr, br=layout_b.br)), z=z.tuple, a=a
                )
            case StageBorderStyle.DISABLED:
                pass
            case _:
                assert_never(style)

    def draw_dividers(division_size: int, parity: DivisionParity, pivot: float, z: ZIndexes, a: float):
        eps = 0.001
        parity_offset = division_size / 2 if parity == DivisionParity.ODD else 0
        shifted_pivot = pivot + parity_offset

        if division_size <= 0:
            return

        k_start = floor((l - shifted_pivot + eps) / division_size) + 1
        k_end = ceil((r - shifted_pivot - eps) / division_size) - 1

        for k in range(k_start, k_end + 1):
            pos = shifted_pivot + k * division_size
            div_layout_b = layout_stage_lane_by_edges(pos - 0.0125, pos + 0.0125)
            div_layout_t = layout_stage_lane_by_edges(
                tilt_widened_edge(pos - 0.0125, pos - 0.1), tilt_widened_edge(pos + 0.0125, pos + 0.1)
            )
            ActiveSkin.lane_divider.draw(
                place(Quad(bl=div_layout_b.bl, tl=div_layout_t.tl, tr=div_layout_t.tr, br=div_layout_b.br)),
                z=z.tuple,
                a=a,
            )

    thickness_scale = lerp(1.0, clamp(1 / travel, 1, 4) if travel > 0 else 4, current_stage_tilt())
    judgment_divider_size = 0.014 * thickness_scale * tilt_width_factor(travel) * DynamicLayout.w_scale
    judgment_divider_offset = Vec2(judgment_divider_size, 0).rotate(-DynamicLayout.rotate)
    divider_depth_b = tilt_depth(1 + nh - nh / f + 0.001, travel)
    divider_depth_t = tilt_depth(1 - nh + nh / f - 0.001, travel)

    def layout_judgment_divider(lane: float):
        b = transformed_vec_at(lane, divider_depth_b)
        t = transformed_vec_at(lane, divider_depth_t)
        return Quad(
            bl=b - judgment_divider_offset,
            tl=t - judgment_divider_offset,
            tr=t + judgment_divider_offset,
            br=b + judgment_divider_offset,
        )

    def draw_judgment_dividers(
        sprites: JudgmentSpriteSet, half_offset: bool, pivot: float, z_lo: ZIndexes, z_hi: ZIndexes, a: float
    ):
        eps = 0.001
        shifted_pivot = pivot + (0.5 if half_offset else 0)

        k_start = floor(l - shifted_pivot + eps) + 1
        k_end = ceil(r - shifted_pivot - eps) - 1

        for k in range(k_start, k_end + 1):
            pos = shifted_pivot + k
            div_layout = place(layout_judgment_divider(pos))
            edge_weight = abs(pos - lane) / width if width > 0 else 0
            sprites.judgment_center.draw(div_layout, z=z_lo.tuple, a=a)
            sprites.judgment_edge.draw(div_layout, z=z_hi.tuple, a=a * edge_weight)

    def draw_left_judgment_border(sprites: JudgmentSpriteSet, style: StageBorderStyle, z: ZIndexes, a: float):
        match style:
            case StageBorderStyle.DEFAULT | StageBorderStyle.MEDIUM:
                if width <= 0:
                    return
                layout = place(
                    perspective_rect(
                        l,
                        min(l + 1 / f / 2, lane),
                        1 - nh + nh / f,
                        1 + nh - nh / f,
                        travel,
                    )
                )
                sprites.judgment_edge_left.draw(layout, z=z.tuple, a=a)
            case StageBorderStyle.LIGHT:
                layout = place(layout_judgment_divider(l))
                sprites.judgment_edge.draw(layout, z=z.tuple, a=a)
            case StageBorderStyle.DISABLED:
                pass
            case _:
                assert_never(style)

    def draw_right_judgment_border(sprites: JudgmentSpriteSet, style: StageBorderStyle, z: ZIndexes, a: float):
        match style:
            case StageBorderStyle.DEFAULT | StageBorderStyle.MEDIUM:
                if width <= 0:
                    return
                layout = place(
                    perspective_rect(
                        r,
                        max(r - 1 / f / 2, lane),
                        1 - nh + nh / f,
                        1 + nh - nh / f,
                        travel,
                    )
                )
                sprites.judgment_edge_left.draw(layout, z=z.tuple, a=a)
            case StageBorderStyle.LIGHT:
                layout = place(layout_judgment_divider(r))
                sprites.judgment_edge.draw(layout, z=z.tuple, a=a)
            case StageBorderStyle.DISABLED:
                pass
            case _:
                assert_never(style)

    def draw_gradient(sprites: JudgmentSpriteSet, z: ZIndexes, a: float):
        bottom_l = place(perspective_rect(l_jl, lane, 1 + nh, 1 + nh - nh / f, travel))
        bottom_r = place(perspective_rect(r_jl, lane, 1 + nh, 1 + nh - nh / f, travel))
        top_l = place(perspective_rect(l_jl, lane, 1 - nh, 1 - nh + nh / f, travel))
        top_r = place(perspective_rect(r_jl, lane, 1 - nh, 1 - nh + nh / f, travel))
        grad_a = a * (1 - fw)
        edge_a = a * fw
        if grad_a > 0:
            sprites.judgment_gradient.draw(bottom_l, z=z.tuple, a=grad_a)
            sprites.judgment_gradient.draw(bottom_r, z=z.tuple, a=grad_a)
            sprites.judgment_gradient.draw(top_l, z=z.tuple, a=grad_a)
            sprites.judgment_gradient.draw(top_r, z=z.tuple, a=grad_a)
        if edge_a > 0:
            sprites.judgment_edge.draw(bottom_l, z=z.tuple, a=edge_a)
            sprites.judgment_edge.draw(bottom_r, z=z.tuple, a=edge_a)
            sprites.judgment_edge.draw(top_l, z=z.tuple, a=edge_a)
            sprites.judgment_edge.draw(top_r, z=z.tuple, a=edge_a)

    def draw_single_line(sprites: JudgmentSpriteSet, z: ZIndexes, a: float):
        half_thick = nh / f / 2
        layout = place(perspective_rect(l_jl, r_jl, 1 - half_thick, 1 + half_thick, travel))
        sprites.judgment_edge.draw(layout, z=z.tuple, a=a)

    la = lane_alpha * (1 - fw)
    if la > 0:
        ActiveSkin.lane_background.draw(place(layout_stage_lane_by_edges(l, r)), z=z_bg0.tuple, a=la)

        p_left = left_border_style.progress
        if left_border_style.start == left_border_style.end:
            draw_left_border(left_border_style.start, z_lane0, la)
        else:
            draw_left_border(left_border_style.start, z_lane0, la * (1 - p_left))
            draw_left_border(left_border_style.end, z_lane1, la * p_left)

        p_right = right_border_style.progress
        if right_border_style.start == right_border_style.end:
            draw_right_border(right_border_style.start, z_lane0, la)
        else:
            draw_right_border(right_border_style.start, z_lane0, la * (1 - p_right))
            draw_right_border(right_border_style.end, z_lane1, la * p_right)

        la_div = la * division_line_alpha
        if la_div > 0:
            p_div = division.progress
            if division.start == division.end:
                draw_dividers(division.start.size, division.start.parity, pivot_lane, z_lane0, la_div)
            else:
                if 1 - p_div > 0:
                    draw_dividers(division.start.size, division.start.parity, pivot_lane, z_lane0, la_div * (1 - p_div))
                if p_div > 0:
                    draw_dividers(division.end.size, division.end.parity, pivot_lane, z_lane1, la_div * p_div)

    ja = judge_line_alpha
    ja_bar = ja * w_default
    ja_dec = ja_bar * (1 - fw)
    ja_single = ja * w_single_line

    if ja_bar > 0:
        bg_layout = place(perspective_rect(l_jl, r_jl, 1 - nh, 1 + nh, travel))
        if sprites_same:
            sprites_a.judgment_background.draw(bg_layout, z=z_bg1_a.tuple, a=ja_bar)
        else:
            sprites_a.judgment_background.draw(bg_layout, z=z_bg1_a.tuple, a=ja_bar * (1 - p_sprites))
            sprites_b.judgment_background.draw(bg_layout, z=z_bg1_b.tuple, a=ja_bar * p_sprites)

    p_left = left_border_style.progress
    p_right = right_border_style.progress
    p_div = division.progress

    start_has_half_offset = division.start.parity == DivisionParity.ODD and division.start.size % 2 == 1
    end_has_half_offset = division.end.parity == DivisionParity.ODD and division.end.size % 2 == 1
    judgment_dividers_same = start_has_half_offset == end_has_half_offset

    if ja_dec > 0:
        if judgment_dividers_same and sprites_same:
            draw_judgment_dividers(sprites_a, start_has_half_offset, pivot_lane, z_a0, z_a1, ja_dec)
        elif judgment_dividers_same:
            draw_judgment_dividers(sprites_a, start_has_half_offset, pivot_lane, z_a0, z_a1, ja_dec * (1 - p_sprites))
            draw_judgment_dividers(sprites_b, start_has_half_offset, pivot_lane, z_b0, z_b1, ja_dec * p_sprites)
        elif sprites_same:
            draw_judgment_dividers(sprites_a, start_has_half_offset, pivot_lane, z_a0, z_a1, ja_dec * (1 - p_div))
            draw_judgment_dividers(sprites_a, end_has_half_offset, pivot_lane, z_a2, z_a3, ja_dec * p_div)
        else:
            alpha_aa = (1 - p_sprites) * (1 - p_div)
            alpha_ab = (1 - p_sprites) * p_div
            alpha_ba = p_sprites * (1 - p_div)
            alpha_bb = p_sprites * p_div
            if alpha_aa > 0:
                draw_judgment_dividers(sprites_a, start_has_half_offset, pivot_lane, z_a0, z_a1, ja_dec * alpha_aa)
            if alpha_ab > 0:
                draw_judgment_dividers(sprites_a, end_has_half_offset, pivot_lane, z_a2, z_a3, ja_dec * alpha_ab)
            if alpha_ba > 0:
                draw_judgment_dividers(sprites_b, start_has_half_offset, pivot_lane, z_b0, z_b1, ja_dec * alpha_ba)
            if alpha_bb > 0:
                draw_judgment_dividers(sprites_b, end_has_half_offset, pivot_lane, z_b2, z_b3, ja_dec * alpha_bb)

    if ja_bar > 0:
        if sprites_same:
            draw_gradient(sprites_a, z_a4, ja_bar)
        else:
            draw_gradient(sprites_a, z_a4, ja_bar * (1 - p_sprites))
            draw_gradient(sprites_b, z_b4, ja_bar * p_sprites)

    if ja_dec > 0:
        if sprites_same and left_border_style.start == left_border_style.end:
            draw_left_judgment_border(sprites_a, left_border_style.start, z_a0, ja_dec)
        else:
            alpha_aa = (1 - p_sprites) * (1 - p_left)
            alpha_ab = (1 - p_sprites) * p_left
            alpha_ba = p_sprites * (1 - p_left)
            alpha_bb = p_sprites * p_left
            if alpha_aa > 0:
                draw_left_judgment_border(sprites_a, left_border_style.start, z_a0, ja_dec * alpha_aa)
            if alpha_ab > 0:
                draw_left_judgment_border(sprites_a, left_border_style.end, z_a2, ja_dec * alpha_ab)
            if alpha_ba > 0:
                draw_left_judgment_border(sprites_b, left_border_style.start, z_b0, ja_dec * alpha_ba)
            if alpha_bb > 0:
                draw_left_judgment_border(sprites_b, left_border_style.end, z_b2, ja_dec * alpha_bb)

        if sprites_same and right_border_style.start == right_border_style.end:
            draw_right_judgment_border(sprites_a, right_border_style.start, z_a0, ja_dec)
        else:
            alpha_aa = (1 - p_sprites) * (1 - p_right)
            alpha_ab = (1 - p_sprites) * p_right
            alpha_ba = p_sprites * (1 - p_right)
            alpha_bb = p_sprites * p_right
            if alpha_aa > 0:
                draw_right_judgment_border(sprites_a, right_border_style.start, z_a0, ja_dec * alpha_aa)
            if alpha_ab > 0:
                draw_right_judgment_border(sprites_a, right_border_style.end, z_a2, ja_dec * alpha_ab)
            if alpha_ba > 0:
                draw_right_judgment_border(sprites_b, right_border_style.start, z_b0, ja_dec * alpha_ba)
            if alpha_bb > 0:
                draw_right_judgment_border(sprites_b, right_border_style.end, z_b2, ja_dec * alpha_bb)

    if ja_single > 0:
        if sprites_same:
            draw_single_line(sprites_a, z_single_a, ja_single)
        else:
            draw_single_line(sprites_a, z_single_a, ja_single * (1 - p_sprites))
            draw_single_line(sprites_b, z_single_b, ja_single * p_sprites)


def draw_fallback_stage(
    lane: float,
    width: float,
    division_size: int,
    parity: DivisionParity,
    pivot: float,
    z: int,
    lane_alpha: float = 1,
    judge_line_alpha: float = 1,
    y_offset: float = 0,
    judge_line_style: Transition[JudgeLineStyle] | JudgeLineStyle = JudgeLineStyle.DEFAULT,
    full_width: float = 0,
    *,
    transform: AffineTransform2d,
):
    def place(q: QuadLike) -> QuadLike:
        return transform.transform_quad(q)

    judge_line_style = normalize_transition(judge_line_style)
    w_default = judge_line_style_weight(judge_line_style, JudgeLineStyle.DEFAULT)
    w_single_line = judge_line_style_weight(judge_line_style, JudgeLineStyle.SINGLE_LINE)
    travel = judgment_approach(1, y_offset)
    nh = DynamicLayout.note_h
    l = lane - width
    r = lane + width
    fw = clamp(full_width, 0, 1)
    half_jl = lerp(width, FULL_WIDTH_HALF_EXTENT, fw)
    l_jl = lane - half_jl
    r_jl = lane + half_jl
    z_lo = get_z_alt(LAYER_STAGE, z * 4)
    z_mid = get_z_alt(LAYER_STAGE, z * 4 + 1)
    z_hi = get_z_alt(LAYER_STAGE, z * 4 + 2)
    z_single = get_z_alt(LAYER_STAGE, z * 4 + 3)
    la = lane_alpha * (1 - fw)
    ja = judge_line_alpha
    if la > 0:
        # Artificially thicken the top so it renders better
        layout_b = layout_stage_lane_by_edges(l - 0.25, l)
        layout_t = layout_stage_lane_by_edges(tilt_widened_edge(l - 0.25, l - 1), l)
        ActiveSkin.stage_left_border.draw(
            place(Quad(bl=layout_b.bl, tl=layout_t.tl, tr=layout_t.tr, br=layout_b.br)), z=z_mid.tuple, a=la
        )
        layout_b = layout_stage_lane_by_edges(r, r + 0.25)
        layout_t = layout_stage_lane_by_edges(r, tilt_widened_edge(r + 0.25, r + 1))
        ActiveSkin.stage_right_border.draw(
            place(Quad(bl=layout_b.bl, tl=layout_t.tl, tr=layout_t.tr, br=layout_b.br)), z=z_mid.tuple, a=la
        )

        eps = 0.001
        parity_offset = division_size / 2 if parity == DivisionParity.ODD else 0
        shifted_pivot = pivot + parity_offset
        prev = l
        if division_size > 0:
            k_start = floor((l - shifted_pivot + eps) / division_size) + 1
            k_end = ceil((r - shifted_pivot - eps) / division_size) - 1
            for k in range(k_start, k_end + 1):
                pos = shifted_pivot + k * division_size
                ActiveSkin.lane.draw(place(layout_stage_lane_by_edges(prev, pos)), a=la, z=z_lo.tuple)
                prev = pos
        ActiveSkin.lane.draw(place(layout_stage_lane_by_edges(prev, r)), a=la, z=z_lo.tuple)

    if ja * w_default > 0:
        layout = place(perspective_rect(l_jl, r_jl, t=1 - nh, b=1 + nh, travel=travel))
        ActiveSkin.judgment_line.draw(layout, z=z_hi.tuple, a=ja * w_default)
    if ja * w_single_line > 0:
        half_thick = nh / JUDGE_LINE_BORDER_FACTOR / 2
        layout = place(perspective_rect(l_jl, r_jl, t=1 - half_thick, b=1 + half_thick, travel=travel))
        ActiveSkin.judgment_line.draw(layout, z=z_single.tuple, a=ja * w_single_line)


def draw_stage_cover():
    if Options.stage_cover > 0:
        layout = layout_visibility_line(DynamicLayout.progress_start)
        ActiveSkin.guide_neutral.draw(layout, z=get_z(LAYER_COVER).tuple)
    if Options.hidden > 0:
        layout = layout_visibility_line(DynamicLayout.progress_cutoff)
        ActiveSkin.guide_neutral.draw(layout, z=get_z(LAYER_COVER).tuple)


def play_lane_hit_effects(lane: float, sfx: bool = True, *, transform: AffineTransform2d):
    if sfx:
        play_lane_sfx(lane)
    play_lane_particle(lane, transform)


def play_lane_sfx(lane: float):
    if Options.sfx_enabled:
        Effects.stage.play(SFX_DISTANCE)


def schedule_lane_sfx(lane: float, target_time: float):
    if Options.sfx_enabled:
        Effects.stage.schedule(target_time, SFX_DISTANCE)


def play_lane_particle(lane: float, transform: AffineTransform2d):
    if Options.lane_effect_enabled:
        layout = transform.transform_quad(layout_particle_lane(lane, 0.5))
        ActiveParticles.lane.spawn(layout, duration=0.3 / Options.effect_animation_speed)
