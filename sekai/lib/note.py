from collections.abc import Iterable
from enum import IntEnum, auto
from typing import Literal, assert_never, cast

from sonolus.script.archetype import EntityRef, HapticType, PlayArchetype, WatchArchetype, get_archetype_by_name
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.effect import Effect
from sonolus.script.interval import lerp, remap_clamped, unlerp_clamped
from sonolus.script.quad import Quad
from sonolus.script.runtime import is_tutorial, is_watch, level_life, level_score, time
from sonolus.script.sprite import Sprite
from sonolus.script.vec import Vec2

from sekai.lib import archetype_names
from sekai.lib.buckets import (
    EMPTY_JUDGMENT_WINDOW,
    SLIDE_END_FLICK_WINDOW,
    SLIDE_END_TRACE_WINDOW,
    SLIDE_TICK_JUDGMENT_WINDOW,
    TAP_WINDOW,
    TRACE_FLICK_WINDOW,
    Buckets,
    SekaiWindow,
)
from sekai.lib.connector import ActiveConnectorKind, ConnectorKind
from sekai.lib.ease import EaseType, ease
from sekai.lib.effect import EMPTY_EFFECT, SFX_DISTANCE, Effects, first_available_effect
from sekai.lib.layer import (
    LAYER_NOTE_ARROW,
    LAYER_NOTE_BODY,
    LAYER_NOTE_TICK,
    LAYER_OVERLAY,
    ZIndexes,
    get_z,
    get_z_alt,
)
from sekai.lib.layout import (
    IDENTITY_AFFINE_TRANSFORM,
    AffineTransform2d,
    DynamicLayout,
    Hitbox,
    approach,
    get_alpha,
    iter_slot_lanes,
    layout_circular_effect,
    layout_flick_arrow,
    layout_flick_arrow_fallback,
    layout_linear_effect,
    layout_note_icon,
    layout_particle_lane,
    layout_regular_note_body,
    layout_regular_note_body_fallback,
    layout_rotated_linear_effect,
    layout_slim_note_body,
    layout_slim_note_body_fallback,
    layout_tick,
    layout_tick_effect,
    preempt_time,
    progress_to,
)
from sekai.lib.options import Options, VibrateMode
from sekai.lib.particle import (
    EMPTY_NOTE_PARTICLE_SET,
    ActiveParticles,
    NoteParticleSet,
)
from sekai.lib.skin import (
    EMPTY_NOTE_SPRITE_SET,
    ActiveSkin,
    ArrowRenderType,
    ArrowSpriteSet,
    BodyRenderType,
    BodySpriteSet,
    NoteSpriteSet,
)
from sekai.lib.slot_effect import (
    SLOT_EFFECT_DURATION,
    SLOT_GLOW_EFFECT_DURATION,
    draw_slot_effect,
    draw_slot_glow_effect,
)
from sekai.lib.timescale import (
    CompositeTime,
    group_force_note_speed,
    group_scaled_time_to_first_time,
    group_scaled_time_to_first_time_2,
)


class NoteKind(IntEnum):
    NORM_TAP = auto()
    CRIT_TAP = auto()

    NORM_TRACE_FLICK = auto()
    CRIT_TRACE_FLICK = auto()

    NORM_HEAD_TAP = auto()
    CRIT_HEAD_TAP = auto()

    NORM_TAIL_FLICK = auto()
    CRIT_TAIL_FLICK = auto()

    NORM_TAIL_TRACE = auto()
    CRIT_TAIL_TRACE = auto()

    NORM_TICK = auto()
    CRIT_TICK = auto()
    HIDE_TICK = auto()

    DAMAGE = auto()

    ANCHOR = auto()


def init_score(note_archetypes: Iterable[type[PlayArchetype | WatchArchetype]]):
    level_score().update(
        perfect_multiplier=1.0,
        great_multiplier=0.8,
        good_multiplier=0.5,
    )

    for note_archetype in note_archetypes:
        kind = cast(NoteKind, note_archetype.key)
        match kind:
            case NoteKind.NORM_TAP | NoteKind.NORM_HEAD_TAP:
                weight = 10
            case NoteKind.CRIT_TAP | NoteKind.CRIT_HEAD_TAP:
                weight = 10
            case NoteKind.NORM_TAIL_FLICK:
                weight = 10
            case NoteKind.CRIT_TAIL_FLICK:
                weight = 10
            case NoteKind.NORM_TAIL_TRACE:
                weight = 10
            case NoteKind.CRIT_TAIL_TRACE:
                weight = 10
            case NoteKind.NORM_TRACE_FLICK:
                weight = 10
            case NoteKind.CRIT_TRACE_FLICK:
                weight = 10
            case NoteKind.NORM_TICK | NoteKind.CRIT_TICK | NoteKind.HIDE_TICK:
                weight = 1
            case NoteKind.DAMAGE:
                weight = 1
            case NoteKind.ANCHOR:
                weight = 1  # Doesn't really matter since anchors are not scored
            case _:
                assert_never(kind)
        note_archetype.archetype_score_multiplier = weight


def init_life(
    note_archetypes: Iterable[type[PlayArchetype | WatchArchetype]],
    initial_life: int,
):
    for note_archetype in note_archetypes:
        init_note_life(note_archetype)
    level_life().update(initial=initial_life, maximum=initial_life)


def init_note_life(archetype: type[PlayArchetype | WatchArchetype]):
    kind = cast(NoteKind, archetype.key)
    match kind:
        case (
            NoteKind.NORM_TAP
            | NoteKind.CRIT_TAP
            | NoteKind.NORM_TRACE_FLICK
            | NoteKind.CRIT_TRACE_FLICK
            | NoteKind.NORM_HEAD_TAP
            | NoteKind.CRIT_HEAD_TAP
            | NoteKind.NORM_TAIL_FLICK
            | NoteKind.CRIT_TAIL_FLICK
            | NoteKind.NORM_TAIL_TRACE
            | NoteKind.CRIT_TAIL_TRACE
        ):
            archetype.life.miss_increment = -100
        case NoteKind.NORM_TICK | NoteKind.CRIT_TICK | NoteKind.HIDE_TICK:
            archetype.life.miss_increment = -20
        case NoteKind.DAMAGE:
            archetype.life.miss_increment = -50
        case NoteKind.ANCHOR:
            pass
        case _:
            assert_never(kind)


def map_note_kind(kind: NoteKind) -> NoteKind:
    return kind


def get_visual_spawn_time(
    timescale_group: int | EntityRef,
    target_scaled_time: CompositeTime | float,
):
    if isinstance(target_scaled_time, CompositeTime):
        target_scaled_time = target_scaled_time.total
    force_speed = group_force_note_speed(timescale_group)
    return min(
        group_scaled_time_to_first_time(timescale_group, target_scaled_time - preempt_time(force_speed) * 3),
        group_scaled_time_to_first_time_2(timescale_group, target_scaled_time + preempt_time(force_speed) * 3),
        -2 if -3 <= progress_to(target_scaled_time, -2, force_speed) <= 6 else 1e8,
    )


def get_attach_params(
    ease_type: EaseType,
    head_lane: float,
    head_size: float,
    head_target_time: float,
    tail_lane: float,
    tail_size: float,
    tail_target_time: float,
    target_time: float,
):
    if abs(head_target_time - tail_target_time) < 1e-6:
        frac = 0.5
    else:
        frac = remap_clamped(head_target_time, tail_target_time, 0.0, 1.0, target_time)
    eased_frac = ease(ease_type, frac)
    lane = lerp(head_lane, tail_lane, eased_frac)
    size = lerp(head_size, tail_size, eased_frac)
    return lane, size


def draw_note(
    kind: NoteKind,
    lane: float,
    size: float,
    visual_progress: float,
    target_time: float,
    transform: AffineTransform2d,
    note_alpha: float,
):
    if not DynamicLayout.progress_start <= visual_progress <= DynamicLayout.progress_cutoff:
        return
    if note_alpha <= 0:
        return
    travel = approach(visual_progress)
    sprite_set = get_note_sprite_set(kind)
    draw_note_body(sprite_set.body, kind, lane, size, travel, target_time, transform, note_alpha)
    draw_note_arrow(sprite_set.arrow, kind, lane, size, travel, target_time, transform, note_alpha)
    draw_note_tick(sprite_set.tick, lane, travel, target_time, transform, note_alpha)
    draw_note_icon(kind, lane, travel, target_time, transform, note_alpha)


def draw_slide_note_head(
    kind: NoteKind,
    connector_kind: ActiveConnectorKind | Literal[ConnectorKind.DAMAGE],
    lane: float,
    size: float,
    target_time: float,
    visual_progress: float = 1.0,
    *,
    transform: AffineTransform2d,
    note_alpha: float,
):
    if Options.hidden > 0:
        return
    if note_alpha <= 0:
        return
    match connector_kind:
        case ConnectorKind.ACTIVE_NORMAL | ConnectorKind.ACTIVE_FAKE_NORMAL:
            kind = note_kind_as_normal(kind)
        case ConnectorKind.ACTIVE_CRITICAL | ConnectorKind.ACTIVE_FAKE_CRITICAL:
            kind = note_kind_as_critical(kind)
        case ConnectorKind.DAMAGE:
            pass  # Keep kind as is
        case _:
            assert_never(connector_kind)
    travel = approach(visual_progress)
    sprite_set = get_note_sprite_set(kind)
    draw_note_body(sprite_set.body, kind, lane, size, travel, target_time, transform, note_alpha)
    draw_note_tick(sprite_set.tick, lane, travel, target_time, transform, note_alpha)
    draw_note_icon(kind, lane, travel, target_time, transform, note_alpha)


def note_kind_as_normal(kind: NoteKind) -> NoteKind:
    match kind:
        case NoteKind.CRIT_TAP:
            return NoteKind.NORM_TAP
        case NoteKind.CRIT_TRACE_FLICK:
            return NoteKind.NORM_TRACE_FLICK
        case NoteKind.CRIT_HEAD_TAP:
            return NoteKind.NORM_HEAD_TAP
        case NoteKind.CRIT_TAIL_TRACE:
            return NoteKind.NORM_TAIL_TRACE
        case NoteKind.CRIT_TAIL_FLICK:
            return NoteKind.NORM_TAIL_FLICK
        case NoteKind.CRIT_TICK:
            return NoteKind.NORM_TICK
        case _:
            return kind


def note_kind_as_critical(kind: NoteKind) -> NoteKind:
    match kind:
        case NoteKind.NORM_TAP:
            return NoteKind.CRIT_TAP
        case NoteKind.NORM_TRACE_FLICK:
            return NoteKind.CRIT_TRACE_FLICK
        case NoteKind.NORM_HEAD_TAP:
            return NoteKind.CRIT_HEAD_TAP
        case NoteKind.NORM_TAIL_FLICK:
            return NoteKind.CRIT_TAIL_FLICK
        case NoteKind.NORM_TAIL_TRACE:
            return NoteKind.CRIT_TAIL_TRACE
        case NoteKind.NORM_TICK:
            return NoteKind.CRIT_TICK
        case _:
            return kind


def get_note_sprite_set(kind: NoteKind) -> NoteSpriteSet:
    result = +NoteSpriteSet
    match kind:
        case NoteKind.NORM_TAP:
            result @= ActiveSkin.normal_note
        case NoteKind.CRIT_TAP:
            result @= ActiveSkin.critical_note
        case NoteKind.NORM_TAIL_FLICK:
            result @= ActiveSkin.flick_note
        case NoteKind.CRIT_TAIL_FLICK:
            result @= ActiveSkin.critical_flick_note
        case NoteKind.NORM_TAIL_TRACE:
            result @= ActiveSkin.trace_note
        case NoteKind.CRIT_TAIL_TRACE:
            result @= ActiveSkin.critical_trace_note
        case NoteKind.NORM_TRACE_FLICK:
            result @= ActiveSkin.trace_flick_note
        case NoteKind.CRIT_TRACE_FLICK:
            result @= ActiveSkin.critical_trace_flick_note
        case NoteKind.NORM_HEAD_TAP:
            result @= ActiveSkin.slide_note
        case NoteKind.CRIT_HEAD_TAP:
            result @= ActiveSkin.critical_slide_note
        case NoteKind.NORM_TICK:
            result @= ActiveSkin.normal_slide_tick_note
        case NoteKind.CRIT_TICK:
            result @= ActiveSkin.critical_slide_tick_note
        case NoteKind.HIDE_TICK | NoteKind.ANCHOR:
            result @= EMPTY_NOTE_SPRITE_SET
        case NoteKind.DAMAGE:
            result @= ActiveSkin.damage_note
        case _:
            assert_never(kind)
    return result


def get_note_body_layer(_kind: NoteKind) -> int:
    return LAYER_NOTE_BODY


def draw_note_body(
    sprites: BodySpriteSet,
    kind: NoteKind,
    lane: float,
    size: float,
    travel: float,
    target_time: float,
    transform: AffineTransform2d,
    note_alpha: float,
):
    layer = get_note_body_layer(kind)
    a = min(get_alpha(target_time) * note_alpha, 1.0)
    z = get_z(layer, time=target_time, lane=lane)

    def place(q):
        return transform.transform_quad(q)

    match sprites.render_type:
        case BodyRenderType.NORMAL:
            left_layout, middle_layout, right_layout = layout_regular_note_body(lane, size, travel)
            sprites.left.draw(place(left_layout), z=z.tuple, a=a)
            sprites.middle.draw(place(middle_layout), z=z.tuple, a=a)
            sprites.right.draw(place(right_layout), z=z.tuple, a=a)
        case BodyRenderType.SLIM:
            left_layout, middle_layout, right_layout = layout_slim_note_body(lane, size, travel)
            sprites.left.draw(place(left_layout), z=z.tuple, a=a)
            sprites.middle.draw(place(middle_layout), z=z.tuple, a=a)
            sprites.right.draw(place(right_layout), z=z.tuple, a=a)
        case BodyRenderType.NORMAL_FALLBACK:
            layout = layout_regular_note_body_fallback(lane, size, travel)
            sprites.middle.draw(place(layout), z=z.tuple, a=a)
        case BodyRenderType.SLIM_FALLBACK:
            layout = layout_slim_note_body_fallback(lane, size, travel)
            sprites.middle.draw(place(layout), z=z.tuple, a=a)


def draw_note_tick(
    sprite: Sprite, lane: float, travel: float, target_time: float, transform: AffineTransform2d, note_alpha: float
):
    a = min(get_alpha(target_time) * note_alpha, 1.0)
    z = get_z(LAYER_NOTE_TICK, time=target_time, lane=lane)
    layout = transform.transform_quad(layout_tick(lane, travel))
    sprite.draw(layout, z=z.tuple, a=a)


def draw_note_icon(
    kind: NoteKind,
    lane: float,
    travel: float,
    target_time: float,
    transform: AffineTransform2d,
    note_alpha: float,
):
    match kind:
        case (
            NoteKind.NORM_TAP
            | NoteKind.CRIT_TAP
            | NoteKind.NORM_TRACE_FLICK
            | NoteKind.CRIT_TRACE_FLICK
            | NoteKind.NORM_HEAD_TAP
            | NoteKind.CRIT_HEAD_TAP
            | NoteKind.NORM_TAIL_FLICK
            | NoteKind.CRIT_TAIL_FLICK
            | NoteKind.NORM_TAIL_TRACE
            | NoteKind.CRIT_TAIL_TRACE
            | NoteKind.DAMAGE
        ):
            pass
        case _:
            return
    a = min(get_alpha(target_time) * note_alpha, 1.0)
    z = get_z(get_note_body_layer(kind), time=target_time, lane=lane, etc=1)
    layout = transform.transform_quad(layout_note_icon(lane, travel))
    ActiveSkin.note_icon.draw(layout, z=z.tuple, a=a)


def draw_note_arrow(
    sprites: ArrowSpriteSet,
    kind: NoteKind,
    lane: float,
    size: float,
    travel: float,
    target_time: float,
    transform: AffineTransform2d,
    note_alpha: float,
):
    a = min(get_alpha(target_time) * note_alpha, 1.0)
    z = get_z(LAYER_NOTE_ARROW, time=target_time, lane=lane, etc=not is_critical(kind))
    match sprites.render_type:
        case ArrowRenderType.NORMAL:
            layout = transform.transform_quad(layout_flick_arrow(lane, size, travel))
            sprites.get_sprite(size).draw(layout, z=z.tuple, a=a)
        case ArrowRenderType.FALLBACK:
            layout = transform.transform_quad(layout_flick_arrow_fallback(lane, size, travel))
            sprites.get_sprite(size).draw(layout, z=z.tuple, a=a)


def get_note_particles(kind: NoteKind) -> NoteParticleSet:
    result = +NoteParticleSet
    match kind:
        case NoteKind.NORM_TAP:
            result @= ActiveParticles.normal_note
        case NoteKind.NORM_HEAD_TAP:
            result @= ActiveParticles.slide_note
        case NoteKind.NORM_TAIL_FLICK:
            result @= ActiveParticles.flick_note
        case NoteKind.NORM_TAIL_TRACE:
            result @= ActiveParticles.trace_note
        case NoteKind.NORM_TRACE_FLICK:
            result @= ActiveParticles.trace_flick_note
        case NoteKind.CRIT_TAP:
            result @= ActiveParticles.critical_note
        case NoteKind.CRIT_HEAD_TAP:
            result @= ActiveParticles.critical_slide_note
        case NoteKind.CRIT_TAIL_FLICK:
            result @= ActiveParticles.critical_flick_note
        case NoteKind.CRIT_TAIL_TRACE:
            result @= ActiveParticles.critical_trace_note
        case NoteKind.CRIT_TRACE_FLICK:
            result @= ActiveParticles.critical_trace_flick_note
        case NoteKind.NORM_TICK:
            result @= ActiveParticles.normal_slide_tick_note
        case NoteKind.CRIT_TICK:
            result @= ActiveParticles.critical_slide_tick_note
        case NoteKind.HIDE_TICK | NoteKind.ANCHOR:
            result @= EMPTY_NOTE_PARTICLE_SET
        case NoteKind.DAMAGE:
            result @= ActiveParticles.damage_note
        case _:
            assert_never(kind)
    return result


def get_note_effect(kind: NoteKind, judgment: Judgment):
    result = Effect(-1)
    match kind:
        case NoteKind.NORM_TAP | NoteKind.NORM_HEAD_TAP | NoteKind.CRIT_HEAD_TAP:
            match judgment:
                case Judgment.PERFECT:
                    result @= Effects.normal_perfect
                case Judgment.GREAT:
                    result @= Effects.normal_great
                case Judgment.GOOD:
                    result @= Effects.normal_good
                case Judgment.MISS:
                    result @= EMPTY_EFFECT
                case _:
                    assert_never(judgment)
        case NoteKind.NORM_TRACE_FLICK | NoteKind.NORM_TAIL_FLICK:
            match judgment:
                case Judgment.PERFECT:
                    result @= Effects.flick_perfect
                case Judgment.GREAT:
                    result @= Effects.flick_great
                case Judgment.GOOD:
                    result @= Effects.flick_good
                case Judgment.MISS:
                    result @= EMPTY_EFFECT
                case _:
                    assert_never(judgment)
        case NoteKind.NORM_TAIL_TRACE:
            if judgment != Judgment.MISS:
                result @= first_available_effect(Effects.normal_trace, Effects.normal_perfect)
            else:
                result @= EMPTY_EFFECT
        case NoteKind.NORM_TICK:
            if judgment != Judgment.MISS:
                result @= first_available_effect(Effects.normal_tick, Effects.normal_perfect)
            else:
                result @= EMPTY_EFFECT
        case NoteKind.CRIT_TAP:
            if judgment != Judgment.MISS:
                result @= first_available_effect(Effects.critical_tap, Effects.normal_perfect)
            else:
                result @= EMPTY_EFFECT
        case NoteKind.CRIT_TRACE_FLICK | NoteKind.CRIT_TAIL_FLICK:
            if judgment != Judgment.MISS:
                result @= first_available_effect(Effects.critical_flick, Effects.flick_perfect)
            else:
                result @= EMPTY_EFFECT
        case NoteKind.CRIT_TAIL_TRACE:
            if judgment != Judgment.MISS:
                result @= first_available_effect(Effects.critical_trace, Effects.normal_perfect)
            else:
                result @= EMPTY_EFFECT
        case NoteKind.CRIT_TICK:
            if judgment != Judgment.MISS:
                result @= first_available_effect(Effects.critical_tick, Effects.normal_perfect)
            else:
                result @= EMPTY_EFFECT
        case NoteKind.HIDE_TICK | NoteKind.ANCHOR:
            result @= EMPTY_EFFECT
        case NoteKind.DAMAGE:
            if judgment == Judgment.MISS:
                result @= Effects.normal_good
            else:
                result @= EMPTY_EFFECT
        case _:
            assert_never(kind)
    return result


def play_note_hit_effects(
    kind: NoteKind,
    lane: float,
    size: float,
    judgment: Judgment,
    y_offset: float = 0.0,
    pivot_lane: float = 0.0,
    half_offset: bool = False,
    single_line: bool = False,
    lane_particles: bool = True,
    *,
    transform: AffineTransform2d,
):
    def place(q):
        return transform.transform_quad(q)

    sfx = get_note_effect(kind, judgment)
    if Options.sfx_enabled and not Options.auto_sfx and not is_watch() and sfx.is_available:
        sfx.play(SFX_DISTANCE)
    if kind == NoteKind.DAMAGE and judgment == Judgment.PERFECT:
        return
    particles = get_note_particles(kind)
    if Options.note_effect_enabled:
        if particles.linear.is_available:
            layout = layout_linear_effect(lane, shear=0, y_offset=y_offset)
            particles.linear.spawn(place(layout), duration=0.5 / Options.effect_animation_speed)
        if particles.circular.is_available:
            layout = layout_circular_effect(lane, w=1.75, h=1.05, y_offset=y_offset)
            particles.circular.spawn(place(layout), duration=0.6 / Options.effect_animation_speed)
        if particles.directional.is_available:
            layout = layout_rotated_linear_effect(lane, shear=0, y_offset=y_offset)
            particles.directional.spawn(place(layout), duration=0.32 / Options.effect_animation_speed)
        if particles.tick.is_available:
            layout = layout_tick_effect(lane, y_offset=y_offset)
            particles.tick.spawn(place(layout), duration=0.6 / Options.effect_animation_speed)
        if particles.slot_linear.is_available:
            for slot_lane in iter_slot_lanes(lane, size, pivot_lane=pivot_lane, half_offset=half_offset):
                layout = layout_linear_effect(slot_lane, shear=0, y_offset=y_offset)
                particles.slot_linear.spawn(place(layout), duration=0.5 / Options.effect_animation_speed)
    if Options.lane_effect_enabled and lane_particles:
        lane_y_offset = y_offset if kind == NoteKind.CRIT_TAIL_FLICK else 0.0
        layout = layout_particle_lane(lane, size, y_offset=lane_y_offset)
        if particles.lane.is_available:
            particles.lane.spawn(place(layout), duration=1 / Options.effect_animation_speed)
        elif particles.lane_basic.is_available:
            particles.lane_basic.spawn(place(layout), duration=0.3 / Options.effect_animation_speed)
    if Options.slot_effect_enabled and not is_watch():
        schedule_note_slot_effects(
            kind,
            lane,
            size,
            time(),
            y_offset=y_offset,
            pivot_lane=pivot_lane,
            half_offset=half_offset,
            single_line=single_line,
            transform=transform,
        )


def get_note_haptic_feedback(kind: NoteKind, judgment: Judgment) -> HapticType:
    if judgment == Judgment.MISS and Options.vibrate_mode in {VibrateMode.MISS, VibrateMode.MISS_AND_GOOD}:
        return HapticType.LONG
    if judgment == Judgment.GOOD and Options.vibrate_mode in {VibrateMode.MISS_AND_GOOD}:
        return HapticType.LONG
    if not Options.tap_haptics_enabled or judgment not in {Judgment.PERFECT, Judgment.GREAT}:
        return HapticType.NONE
    match kind:
        case NoteKind.NORM_TAP | NoteKind.NORM_HEAD_TAP | NoteKind.CRIT_TAP | NoteKind.CRIT_HEAD_TAP:
            return HapticType.HEAVY
        case _:
            return HapticType.NONE


def schedule_note_auto_sfx(kind: NoteKind, target_time: float):
    if not Options.sfx_enabled:
        return
    if not Options.auto_sfx:
        return
    sfx = get_note_effect(kind, Judgment.PERFECT)
    if sfx.is_available:
        sfx.schedule(target_time, SFX_DISTANCE)


def schedule_note_sfx(kind: NoteKind, judgment: Judgment, target_time: float):
    if not Options.sfx_enabled:
        return
    sfx = get_note_effect(kind, judgment)
    if sfx.is_available:
        sfx.schedule(target_time, SFX_DISTANCE)


def schedule_note_slot_effects(
    kind: NoteKind,
    lane: float,
    size: float,
    target_time: float,
    y_offset: float = 0.0,
    pivot_lane: float = 0.0,
    half_offset: bool = False,
    single_line: bool = False,
    *,
    transform: AffineTransform2d,
):
    if is_tutorial():
        return
    if not Options.slot_effect_enabled:
        return
    sprite_set = get_note_sprite_set(kind)
    slot_sprite = sprite_set.slot
    if slot_sprite.is_available and not single_line:
        for slot_lane in iter_slot_lanes(lane, size, pivot_lane=pivot_lane, half_offset=half_offset):
            get_archetype_by_name(archetype_names.SLOT_EFFECT).spawn(
                sprite=slot_sprite, start_time=target_time, lane=slot_lane, y_offset=y_offset, transform=transform
            )
    slot_glow_sprite = sprite_set.slot_glow
    if slot_glow_sprite.is_available:
        get_archetype_by_name(archetype_names.SLOT_GLOW_EFFECT).spawn(
            sprite=slot_glow_sprite,
            start_time=target_time,
            lane=lane,
            size=size,
            y_offset=y_offset,
            transform=transform,
        )


def draw_tutorial_note_slot_effects(
    kind: NoteKind,
    lane: float,
    size: float,
    start_time: float,
    pivot_lane: float = 0.0,
    half_offset: bool = False,
    single_line: bool = False,
):
    sprite_set = get_note_sprite_set(kind)
    slot_sprite = sprite_set.slot
    if (
        slot_sprite.is_available
        and not single_line
        and time() < start_time + SLOT_EFFECT_DURATION / Options.effect_animation_speed
    ):
        for slot_lane in iter_slot_lanes(lane, size, pivot_lane=pivot_lane, half_offset=half_offset):
            draw_slot_effect(
                sprite=slot_sprite,
                start_time=start_time,
                end_time=start_time + SLOT_EFFECT_DURATION / Options.effect_animation_speed,
                lane=slot_lane,
                transform=IDENTITY_AFFINE_TRANSFORM,
            )
    slot_glow_sprite = sprite_set.slot_glow
    if (
        slot_glow_sprite.is_available
        and time() < start_time + SLOT_GLOW_EFFECT_DURATION / Options.effect_animation_speed
    ):
        draw_slot_glow_effect(
            sprite=slot_glow_sprite,
            start_time=start_time,
            end_time=start_time + SLOT_GLOW_EFFECT_DURATION / Options.effect_animation_speed,
            lane=lane,
            size=size,
            transform=IDENTITY_AFFINE_TRANSFORM,
        )


INSTANT_HITBOX_DRAW_WINDOW = 0.050
DAMAGE_HITBOX_ACTIVE_WINDOW = 1 / 60


def hitbox_draw_start(kind: NoteKind, input_start_time: float, target_time: float) -> float:
    if kind == NoteKind.DAMAGE:
        return target_time - INSTANT_HITBOX_DRAW_WINDOW
    return input_start_time


def hitbox_draw_alpha(kind: NoteKind, draw_start: float, target_time: float, current_time: float) -> float:
    return unlerp_clamped(draw_start, target_time, current_time)


def get_note_window(kind: NoteKind) -> SekaiWindow:
    result = +SekaiWindow
    match kind:
        case NoteKind.NORM_TAP | NoteKind.NORM_HEAD_TAP | NoteKind.CRIT_TAP | NoteKind.CRIT_HEAD_TAP:
            result @= TAP_WINDOW
        case NoteKind.NORM_TAIL_FLICK:
            result @= SLIDE_END_FLICK_WINDOW
        case NoteKind.CRIT_TAIL_FLICK:
            result @= SLIDE_END_FLICK_WINDOW
        case NoteKind.NORM_TRACE_FLICK | NoteKind.CRIT_TRACE_FLICK:
            result @= TRACE_FLICK_WINDOW
        case NoteKind.NORM_TAIL_TRACE | NoteKind.CRIT_TAIL_TRACE:
            result @= SLIDE_END_TRACE_WINDOW
        case NoteKind.NORM_TICK | NoteKind.CRIT_TICK | NoteKind.HIDE_TICK:
            result @= SLIDE_TICK_JUDGMENT_WINDOW
        case NoteKind.ANCHOR | NoteKind.DAMAGE:
            result @= EMPTY_JUDGMENT_WINDOW
        case _:
            assert_never(kind)
    return result


def get_note_bucket(kind: NoteKind) -> Bucket:
    result = Bucket(-1)
    match kind:
        case NoteKind.NORM_TAP:
            result @= Buckets.normal_tap
        case NoteKind.CRIT_TAP:
            result @= Buckets.critical_tap
        case NoteKind.NORM_TRACE_FLICK:
            result @= Buckets.normal_trace_flick
        case NoteKind.CRIT_TRACE_FLICK:
            result @= Buckets.critical_trace_flick
        case NoteKind.NORM_HEAD_TAP:
            result @= Buckets.normal_head_tap
        case NoteKind.CRIT_HEAD_TAP:
            result @= Buckets.critical_head_tap
        case NoteKind.NORM_TAIL_FLICK:
            result @= Buckets.normal_tail_flick
        case NoteKind.CRIT_TAIL_FLICK:
            result @= Buckets.critical_tail_flick
        case NoteKind.NORM_TAIL_TRACE:
            result @= Buckets.normal_tail_trace
        case NoteKind.CRIT_TAIL_TRACE:
            result @= Buckets.critical_tail_trace
        case NoteKind.NORM_TICK | NoteKind.CRIT_TICK | NoteKind.HIDE_TICK | NoteKind.ANCHOR | NoteKind.DAMAGE:
            result @= Bucket(-1)
        case _:
            assert_never(kind)
    return result


def get_leniency(kind: NoteKind) -> float:
    if kind in {NoteKind.DAMAGE}:
        return 0.0
    # For notes without input, this value doesn't matter
    return 1.0


def has_tap_input(kind: NoteKind) -> bool:
    return kind in {
        NoteKind.NORM_TAP,
        NoteKind.CRIT_TAP,
        NoteKind.NORM_HEAD_TAP,
        NoteKind.CRIT_HEAD_TAP,
    }


def is_head(kind: NoteKind) -> bool:
    return kind in {
        NoteKind.NORM_HEAD_TAP,
        NoteKind.CRIT_HEAD_TAP,
    }


def is_critical(kind: NoteKind) -> bool:
    return kind in {
        NoteKind.CRIT_TAP,
        NoteKind.CRIT_TRACE_FLICK,
        NoteKind.CRIT_HEAD_TAP,
        NoteKind.CRIT_TAIL_FLICK,
        NoteKind.CRIT_TAIL_TRACE,
        NoteKind.CRIT_TICK,
    }


HITBOX_DEBUG_BORDER_THICKNESS = 0.01
HITBOX_DEBUG_END_HALF_HEIGHT = 0.05
HITBOX_DEBUG_END_WIDTH = 0.04
HITBOX_DEBUG_DOT_HALF = 0.012
HITBOX_DEBUG_TRIANGLE_HEIGHT = 0.2
HITBOX_DEBUG_APEX_HALF = 0.012


def draw_hitbox_line(sprite: Sprite, p1: Vec2, p2: Vec2, thickness: float, z: ZIndexes, a: float):
    ortho = (p2 - p1).orthogonal().normalize_or_zero() * (thickness / 2)
    sprite.draw(
        Quad(
            bl=p1 - ortho,
            br=p2 - ortho,
            tr=p2 + ortho,
            tl=p1 + ortho,
        ),
        z=z.tuple,
        a=a,
    )


def draw_hitbox_marker(
    l: Vec2,
    r: Vec2,
    main_sprite: Sprite,
    dot_sprite: Sprite,
    z: ZIndexes,
    z_dot: ZIndexes,
    a: float,
):
    t = HITBOX_DEBUG_BORDER_THICKNESS
    end_h = HITBOX_DEBUG_END_HALF_HEIGHT
    end_w = HITBOX_DEBUG_END_WIDTH
    dot = HITBOX_DEBUG_DOT_HALF
    axis = (r - l).normalize_or_zero()
    ortho = axis.orthogonal()
    li = l + axis * end_w
    ri = r - axis * end_w
    main_sprite.draw(
        Quad(
            bl=li - ortho * t,
            tl=li + ortho * t,
            tr=ri + ortho * t,
            br=ri - ortho * t,
        ),
        z=z.tuple,
        a=a,
    )
    main_sprite.draw(
        Quad(
            bl=l - ortho * end_h,
            tl=l + ortho * end_h,
            tr=li + ortho * t,
            br=li - ortho * t,
        ),
        z=z.tuple,
        a=a,
    )
    main_sprite.draw(
        Quad(
            bl=ri - ortho * t,
            tl=ri + ortho * t,
            tr=r + ortho * end_h,
            br=r - ortho * end_h,
        ),
        z=z.tuple,
        a=a,
    )
    dot_sprite.draw(
        Quad(
            bl=l - ortho * dot,
            tl=l + ortho * dot,
            tr=l + axis * (2 * dot) + ortho * dot,
            br=l + axis * (2 * dot) - ortho * dot,
        ),
        z=z_dot.tuple,
        a=a,
    )
    dot_sprite.draw(
        Quad(
            bl=r - axis * (2 * dot) - ortho * dot,
            tl=r - axis * (2 * dot) + ortho * dot,
            tr=r + ortho * dot,
            br=r - ortho * dot,
        ),
        z=z_dot.tuple,
        a=a,
    )


def get_hitbox_bounds_sprite(kind: NoteKind, time_to_target: float) -> Sprite:
    result = +Sprite
    if kind == NoteKind.DAMAGE:
        if time_to_target > DAMAGE_HITBOX_ACTIVE_WINDOW:
            result @= ActiveSkin.guide_neutral
        else:
            result @= ActiveSkin.guide_green
    else:
        result @= ActiveSkin.guide_blue
    return result


def get_hitbox_target_sprite(kind: NoteKind) -> Sprite:
    result = +Sprite
    if kind in {NoteKind.DAMAGE}:
        result @= ActiveSkin.guide_yellow
    else:
        result @= ActiveSkin.guide_red
    return result


def draw_hitbox_bounds_overlay(bounds: Quad, sprite: Sprite, alpha: float):
    t = HITBOX_DEBUG_BORDER_THICKNESS
    a = alpha
    z_bounds = get_z_alt(LAYER_OVERLAY, 0)
    draw_hitbox_line(sprite, bounds.tl, bounds.tr, t, z_bounds, a)
    draw_hitbox_line(sprite, bounds.bl, bounds.br, t, z_bounds, a)
    draw_hitbox_line(sprite, bounds.tl, bounds.bl, t, z_bounds, a)
    draw_hitbox_line(sprite, bounds.tr, bounds.br, t, z_bounds, a)
    draw_hitbox_line(sprite, bounds.tl, bounds.br, t, z_bounds, a)
    draw_hitbox_line(sprite, bounds.tr, bounds.bl, t, z_bounds, a)


def draw_connector_hitbox_overlay(bounds: Quad, alpha: float):
    draw_hitbox_bounds_overlay(bounds, ActiveSkin.guide_blue, alpha)


def draw_hitbox_overlay(hitbox: Hitbox, kind: NoteKind, alpha: float, *, time_to_target: float):
    t = HITBOX_DEBUG_BORDER_THICKNESS
    a = alpha
    z_triangle = get_z_alt(LAYER_OVERLAY, 1)
    z_apex = get_z_alt(LAYER_OVERLAY, 2)
    z_target = get_z_alt(LAYER_OVERLAY, 3)
    z_target_dot = get_z_alt(LAYER_OVERLAY, 4)

    draw_hitbox_bounds_overlay(hitbox.bounds, get_hitbox_bounds_sprite(kind, time_to_target), alpha)

    if has_tap_input(kind):
        target_sprite = get_hitbox_target_sprite(kind)
        l = hitbox.target.l
        r = hitbox.target.r
        axis = (r - l).normalize_or_zero()
        ortho = axis.orthogonal()
        apex_half = HITBOX_DEBUG_APEX_HALF
        target_apex = (l + r) / 2 + ortho * HITBOX_DEBUG_TRIANGLE_HEIGHT
        draw_hitbox_line(
            target_sprite,
            l,
            target_apex,
            t,
            z_triangle,
            a,
        )
        draw_hitbox_line(
            target_sprite,
            r,
            target_apex,
            t,
            z_triangle,
            a,
        )
        target_sprite.draw(
            Quad(
                bl=target_apex - axis * apex_half - ortho * apex_half,
                tl=target_apex - axis * apex_half + ortho * apex_half,
                tr=target_apex + axis * apex_half + ortho * apex_half,
                br=target_apex + axis * apex_half - ortho * apex_half,
            ),
            z=z_apex.tuple,
            a=a,
        )
        draw_hitbox_marker(
            l=l,
            r=r,
            main_sprite=target_sprite,
            dot_sprite=ActiveSkin.guide_black,
            z=z_target,
            z_dot=z_target_dot,
            a=a,
        )
