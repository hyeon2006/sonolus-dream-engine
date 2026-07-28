from collections.abc import Callable
from math import pi

from sonolus.script.array import Array

from sekai.lib.ease import EaseType, ease
from sekai.lib.layout import FlickDirection, transformed_vec_at
from sekai.lib.note import NoteKind
from sekai.tutorial.framework import PhaseTime, TutorialNoteInfo, zoom_for_intro
from sekai.tutorial.instructions import Instructions
from sekai.tutorial.painting import (
    paint_hold_flick_motion,
    paint_hold_motion,
    paint_tap_flick_motion,
    paint_tap_motion,
)

ANGLE_UP_LEFT = pi / 2 + pi / 4
ANGLE_UP_RIGHT = pi / 2 - pi / 4
ANGLE_DOWN_LEFT = -pi / 2 - pi / 4
ANGLE_DOWN_RIGHT = -pi / 2 + pi / 4
ANGLE_LEFT = pi
ANGLE_RIGHT = 0
OMNI_ANGLES = Array(ANGLE_UP_LEFT, ANGLE_UP_RIGHT, ANGLE_DOWN_RIGHT, ANGLE_DOWN_LEFT)

INTRO_DURATION = 1.5
FALL_DURATION = 1.5
FROZEN_REPEATS = 4
FROZEN_TAP_DURATION = 1
FROZEN_HOLD_DURATION = 1
FROZEN_FLICK_DURATION = 0.5
AVOID_DURATION = 2
END_DURATION = 1.5


MARGIN = 0.1
LANE = 1.5
SIZE = 1.5 - MARGIN


def tap_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_TAP_DURATION, repeats=FROZEN_REPEATS)
    hit = frozen.end_instant()
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)

    norm_note = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TAP,
        lane=-LANE,
        size=SIZE,
    )
    crit_note = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TAP,
        lane=LANE,
        size=SIZE,
    )

    if intro:
        zoom_for_intro()
        norm_note.draw()
        crit_note.draw()
    if fall:
        norm_note.draw(fall.progress)
        crit_note.draw(fall.progress)
    if frozen:
        norm_note.draw()
        crit_note.draw()
        paint_tap_motion(transformed_vec_at(norm_note.lane), frozen.progress)
        paint_tap_motion(transformed_vec_at(crit_note.lane), frozen.progress)
        Instructions.tap.show()
    if hit:
        norm_note.play_hit_effects()
        crit_note.play_hit_effects()
    if post_hit:
        norm_note.draw_slot_effects(post_hit)
        crit_note.draw_slot_effects(post_hit)
    if end:
        pass
    return end.is_done


def omni_flick_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_TAP_DURATION + FROZEN_FLICK_DURATION, repeats=FROZEN_REPEATS)
    hit = t.instant(frozen.end - FROZEN_FLICK_DURATION)
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)

    norm_note = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TAIL_FLICK,
        lane=-LANE,
        size=SIZE,
        direction=FlickDirection.UP_OMNI,
    )
    crit_note = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TAIL_FLICK,
        lane=LANE,
        size=SIZE,
        direction=FlickDirection.DOWN_OMNI,
    )
    if intro:
        zoom_for_intro()
        norm_note.draw()
        crit_note.draw()
    if fall:
        norm_note.draw(fall.progress)
        crit_note.draw(fall.progress)
    if frozen:
        if hit.is_upcoming:
            norm_note.draw()
            crit_note.draw()
        angle = OMNI_ANGLES[frozen.current_segment]
        paint_tap_flick_motion(
            transformed_vec_at(norm_note.lane), angle, frozen.progress, FROZEN_TAP_DURATION, FROZEN_FLICK_DURATION
        )
        paint_tap_flick_motion(
            transformed_vec_at(crit_note.lane), angle, frozen.progress, FROZEN_TAP_DURATION, FROZEN_FLICK_DURATION
        )
        Instructions.tap_flick.show()
    if hit:
        norm_note.play_hit_effects()
        crit_note.play_hit_effects()
    if post_hit:
        norm_note.draw_slot_effects(post_hit)
        crit_note.draw_slot_effects(post_hit)
    if end:
        pass
    return end.is_done


def up_flick_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_TAP_DURATION + FROZEN_FLICK_DURATION, repeats=FROZEN_REPEATS)
    hit = t.instant(frozen.end - FROZEN_FLICK_DURATION)
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)

    norm_note = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TAIL_FLICK,
        lane=-LANE,
        size=SIZE,
        direction=FlickDirection.UP_LEFT,
    )
    crit_note = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TAIL_FLICK,
        lane=LANE,
        size=SIZE,
        direction=FlickDirection.UP_RIGHT,
    )
    if intro:
        zoom_for_intro()
        norm_note.draw()
        crit_note.draw()
    if fall:
        norm_note.draw(fall.progress)
        crit_note.draw(fall.progress)
    if frozen:
        if hit.is_upcoming:
            norm_note.draw()
            crit_note.draw()
        paint_tap_flick_motion(
            transformed_vec_at(norm_note.lane),
            ANGLE_UP_LEFT,
            frozen.progress,
            FROZEN_TAP_DURATION,
            FROZEN_FLICK_DURATION,
        )
        paint_tap_flick_motion(
            transformed_vec_at(crit_note.lane),
            ANGLE_UP_RIGHT,
            frozen.progress,
            FROZEN_TAP_DURATION,
            FROZEN_FLICK_DURATION,
        )
        Instructions.tap_flick.show()
    if hit:
        norm_note.play_hit_effects()
        crit_note.play_hit_effects()
    if post_hit:
        norm_note.draw_slot_effects(post_hit)
        crit_note.draw_slot_effects(post_hit)
    if end:
        pass
    return end.is_done


def down_flick_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_TAP_DURATION + FROZEN_FLICK_DURATION, repeats=FROZEN_REPEATS)
    hit = t.instant(frozen.end - FROZEN_FLICK_DURATION)
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)

    norm_note = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TAIL_FLICK,
        lane=-LANE,
        size=SIZE,
        direction=FlickDirection.DOWN_RIGHT,
    )
    crit_note = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TAIL_FLICK,
        lane=LANE,
        size=SIZE,
        direction=FlickDirection.DOWN_LEFT,
    )
    if intro:
        zoom_for_intro()
        norm_note.draw()
        crit_note.draw()
    if fall:
        norm_note.draw(fall.progress)
        crit_note.draw(fall.progress)
    if frozen:
        if hit.is_upcoming:
            norm_note.draw()
            crit_note.draw()
        paint_tap_flick_motion(
            transformed_vec_at(norm_note.lane),
            ANGLE_DOWN_RIGHT,
            frozen.progress,
            FROZEN_TAP_DURATION,
            FROZEN_FLICK_DURATION,
            offset=True,
        )
        paint_tap_flick_motion(
            transformed_vec_at(crit_note.lane),
            ANGLE_DOWN_LEFT,
            frozen.progress,
            FROZEN_TAP_DURATION,
            FROZEN_FLICK_DURATION,
            offset=True,
        )
        Instructions.tap_flick.show()
    if hit:
        norm_note.play_hit_effects()
        crit_note.play_hit_effects()
    if post_hit:
        norm_note.draw_slot_effects(post_hit)
        crit_note.draw_slot_effects(post_hit)
    if end:
        pass
    return end.is_done


def trace_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_HOLD_DURATION, repeats=FROZEN_REPEATS)
    hit = frozen.end_instant()
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)

    norm_note = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TAIL_TRACE,
        lane=-LANE,
        size=SIZE,
    )
    crit_note = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TAIL_TRACE,
        lane=LANE,
        size=SIZE,
    )
    if intro:
        zoom_for_intro()
        norm_note.draw()
        crit_note.draw()
    if fall:
        norm_note.draw(fall.progress)
        crit_note.draw(fall.progress)
    if frozen:
        norm_note.draw()
        crit_note.draw()
        paint_hold_motion(transformed_vec_at(norm_note.lane))
        paint_hold_motion(transformed_vec_at(crit_note.lane))
        Instructions.hold.show()
    if hit:
        norm_note.play_hit_effects()
        crit_note.play_hit_effects()
    if post_hit:
        norm_note.draw_slot_effects(post_hit)
        crit_note.draw_slot_effects(post_hit)
    if end:
        pass
    return end.is_done


def trace_flick_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_HOLD_DURATION + FROZEN_FLICK_DURATION, repeats=FROZEN_REPEATS)
    hit = t.instant(frozen.end - FROZEN_FLICK_DURATION)
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)

    norm_note = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TRACE_FLICK,
        lane=-LANE,
        size=SIZE,
        direction=FlickDirection.UP_LEFT,
    )
    crit_note = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TRACE_FLICK,
        lane=LANE,
        size=SIZE,
        direction=FlickDirection.UP_RIGHT,
    )
    if intro:
        zoom_for_intro()
        norm_note.draw()
        crit_note.draw()
    if fall:
        norm_note.draw(fall.progress)
        crit_note.draw(fall.progress)
    if frozen:
        if hit.is_upcoming:
            norm_note.draw()
            crit_note.draw()
        paint_hold_flick_motion(
            transformed_vec_at(norm_note.lane),
            ANGLE_LEFT,
            frozen.progress,
            FROZEN_HOLD_DURATION,
            FROZEN_FLICK_DURATION,
        )
        paint_hold_flick_motion(
            transformed_vec_at(crit_note.lane),
            ANGLE_RIGHT,
            frozen.progress,
            FROZEN_HOLD_DURATION,
            FROZEN_FLICK_DURATION,
        )
        Instructions.hold_flick.show()
    if hit:
        norm_note.play_hit_effects()
        crit_note.play_hit_effects()
    if post_hit:
        norm_note.draw_slot_effects(post_hit)
        crit_note.draw_slot_effects(post_hit)
    if end:
        pass
    return end.is_done


def slide_head_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_TAP_DURATION, repeats=FROZEN_REPEATS)
    hit = frozen.end_instant()
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)
    tick_hit = t.instant(post_hit.start + FALL_DURATION / 2)

    norm_head = TutorialNoteInfo.of(
        kind=NoteKind.NORM_HEAD_TAP,
        lane=-LANE,
        size=SIZE,
        offset=0,
    )
    crit_head = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_HEAD_TAP,
        lane=LANE,
        size=SIZE,
        offset=0,
    )
    norm_anchor_1 = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=-LANE - 3,
        size=SIZE,
        offset=-1,
    )
    crit_anchor_1 = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=LANE + 3,
        size=SIZE,
        offset=-1,
    )
    norm_anchor_2 = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=-LANE - 3,
        size=SIZE,
        offset=-2,
    )
    crit_anchor_2 = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=LANE + 3,
        size=SIZE,
        offset=-2,
    )
    norm_tick = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TICK,
        lane=-LANE - 3 * ease(EaseType.OUT_QUAD, 0.5),
        size=SIZE,
        offset=-0.5,
    )
    crit_tick = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TICK,
        lane=LANE + 3 * ease(EaseType.OUT_QUAD, 0.5),
        size=SIZE,
        offset=-0.5,
    )

    if intro:
        zoom_for_intro()
        norm_head.draw()
        crit_head.draw()
        norm_head.draw_connector_to(norm_anchor_1, critical=False, active=False)
        crit_head.draw_connector_to(crit_anchor_1, critical=True, active=False)
    if fall:
        norm_head.draw(fall.progress)
        crit_head.draw(fall.progress)
        norm_head.draw_connector_to(norm_anchor_1, critical=False, active=False, progress=fall.progress)
        crit_head.draw_connector_to(crit_anchor_1, critical=True, active=False, progress=fall.progress)
        norm_anchor_1.draw_connector_to(norm_anchor_2, critical=False, active=False, progress=fall.progress)
        crit_anchor_1.draw_connector_to(crit_anchor_2, critical=True, active=False, progress=fall.progress)
        norm_tick.draw(fall.progress)
        crit_tick.draw(fall.progress)
    if frozen:
        norm_head.draw()
        crit_head.draw()
        norm_head.draw_connector_to(norm_anchor_1, critical=False, active=False)
        crit_head.draw_connector_to(crit_anchor_1, critical=True, active=False)
        norm_anchor_1.draw_connector_to(norm_anchor_2, critical=False, active=False)
        crit_anchor_1.draw_connector_to(crit_anchor_2, critical=True, active=False)
        paint_tap_motion(transformed_vec_at(norm_head.lane), frozen.progress, fade_out=False)
        paint_tap_motion(transformed_vec_at(crit_head.lane), frozen.progress, fade_out=False)
        norm_tick.draw()
        crit_tick.draw()
        Instructions.tap_hold.show()
    if hit:
        norm_head.play_hit_effects()
        crit_head.play_hit_effects()
    if tick_hit:
        norm_tick.play_hit_effects()
        crit_tick.play_hit_effects()
    if post_hit:
        progress = 1 + post_hit.time_since_start / FALL_DURATION
        if tick_hit.is_upcoming:
            norm_tick.draw(progress=progress)
            crit_tick.draw(progress=progress)
        norm_head.draw_slot_effects(post_hit)
        crit_head.draw_slot_effects(post_hit)
        norm_head.draw_connector_to(
            norm_anchor_1,
            critical=False,
            active=True,
            progress=progress,
            active_head_kind=NoteKind.NORM_HEAD_TAP,
            show_touch=True,
            effect_index=0,
        )
        crit_head.draw_connector_to(
            crit_anchor_1,
            critical=True,
            active=True,
            progress=progress,
            active_head_kind=NoteKind.CRIT_HEAD_TAP,
            show_touch=True,
            effect_index=1,
        )
        norm_anchor_1.draw_connector_to(norm_anchor_2, critical=False, active=True, progress=progress)
        crit_anchor_1.draw_connector_to(crit_anchor_2, critical=True, active=True, progress=progress)
        Instructions.hold_follow.show()
    if end:
        pass
    return end.is_done


def slide_tail_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_HOLD_DURATION, repeats=FROZEN_REPEATS)
    hit = frozen.end_instant()
    end = frozen.next(END_DURATION)

    norm_anchor = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=-LANE,
        size=SIZE,
        offset=1,
    )
    crit_anchor = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=LANE,
        size=SIZE,
        offset=1,
    )
    norm_tail = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TAIL_TRACE,
        lane=-LANE,
        size=SIZE,
        offset=0,
    )
    crit_tail = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TAIL_TRACE,
        lane=LANE,
        size=SIZE,
        offset=0,
    )

    if intro:
        progress = 0.95
        zoom_for_intro()
        norm_tail.draw(progress=progress)
        crit_tail.draw(progress=progress)
        norm_anchor.draw_connector_to(norm_tail, critical=False, active=False, progress=progress)
        crit_anchor.draw_connector_to(crit_tail, critical=True, active=False, progress=progress)
    if fall:
        norm_tail.draw(fall.progress)
        crit_tail.draw(fall.progress)
        norm_anchor.draw_connector_to(
            norm_tail, critical=False, active=True, progress=fall.progress, show_touch=True, effect_index=0
        )
        crit_anchor.draw_connector_to(
            crit_tail, critical=True, active=True, progress=fall.progress, show_touch=True, effect_index=1
        )
    if frozen:
        if hit.is_upcoming:
            norm_tail.draw()
            crit_tail.draw()
            norm_anchor.draw_connector_to(norm_tail, critical=False, active=True, show_touch=True, effect_index=0)
            crit_anchor.draw_connector_to(crit_tail, critical=True, active=True, show_touch=True, effect_index=1)
        paint_hold_motion(transformed_vec_at(norm_tail.lane))
        paint_hold_motion(transformed_vec_at(crit_tail.lane))
        Instructions.hold.show()
    if hit:
        norm_tail.play_hit_effects()
        crit_tail.play_hit_effects()
    if end:
        pass
    return end.is_done


def slide_tail_flick_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(FROZEN_HOLD_DURATION + FROZEN_FLICK_DURATION, repeats=FROZEN_REPEATS)
    hit = t.instant(frozen.end - FROZEN_FLICK_DURATION)
    end = frozen.next(END_DURATION)

    norm_anchor = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=-LANE,
        size=SIZE,
        offset=1,
    )
    crit_anchor = TutorialNoteInfo.of(
        kind=NoteKind.ANCHOR,
        lane=LANE,
        size=SIZE,
        offset=1,
    )
    norm_tail = TutorialNoteInfo.of(
        kind=NoteKind.NORM_TAIL_FLICK,
        lane=-LANE,
        size=SIZE,
        direction=FlickDirection.UP_LEFT,
        offset=0,
    )
    crit_tail = TutorialNoteInfo.of(
        kind=NoteKind.CRIT_TAIL_FLICK,
        lane=LANE,
        size=SIZE,
        direction=FlickDirection.UP_RIGHT,
        offset=0,
    )

    if intro:
        progress = 0.95
        zoom_for_intro()
        norm_tail.draw(progress=progress)
        crit_tail.draw(progress=progress)
        norm_anchor.draw_connector_to(norm_tail, critical=False, active=False, progress=progress)
        crit_anchor.draw_connector_to(crit_tail, critical=True, active=False, progress=progress)
    if fall:
        norm_tail.draw(fall.progress)
        crit_tail.draw(fall.progress)
        norm_anchor.draw_connector_to(
            norm_tail, critical=False, active=True, progress=fall.progress, show_touch=True, effect_index=0
        )
        crit_anchor.draw_connector_to(
            crit_tail, critical=True, active=True, progress=fall.progress, show_touch=True, effect_index=1
        )
    if frozen:
        if hit.is_upcoming:
            norm_tail.draw()
            crit_tail.draw()
            norm_anchor.draw_connector_to(norm_tail, critical=False, active=False)
            crit_anchor.draw_connector_to(crit_tail, critical=True, active=False)
        paint_hold_flick_motion(
            transformed_vec_at(norm_tail.lane),
            ANGLE_UP_LEFT,
            frozen.progress,
            FROZEN_HOLD_DURATION,
            FROZEN_FLICK_DURATION,
        )
        paint_hold_flick_motion(
            transformed_vec_at(crit_tail.lane),
            ANGLE_UP_RIGHT,
            frozen.progress,
            FROZEN_HOLD_DURATION,
            FROZEN_FLICK_DURATION,
        )
        Instructions.hold_flick.show()
    if hit:
        norm_tail.play_hit_effects()
        crit_tail.play_hit_effects()
    if end:
        pass
    return end.is_done


def damage_phase(t: PhaseTime):
    intro = t.first(INTRO_DURATION)
    fall = intro.next(FALL_DURATION)
    frozen = fall.next(AVOID_DURATION)
    hit = frozen.end_instant()
    end = frozen.next(END_DURATION)
    post_hit = t.range(hit.timing, end.end)

    dmg_note = TutorialNoteInfo.of(
        kind=NoteKind.DAMAGE,
        lane=0,
        size=2 - MARGIN,
    )

    if intro:
        zoom_for_intro()
        dmg_note.draw()
    if fall:
        dmg_note.draw(fall.progress)
    if frozen:
        dmg_note.draw()
        Instructions.avoid.show()
    if hit:
        pass
    if post_hit:
        pass
    if end:
        pass
    return end.is_done


PHASES: tuple[Callable[[PhaseTime], bool], ...] = (
    tap_phase,
    omni_flick_phase,
    up_flick_phase,
    down_flick_phase,
    trace_phase,
    trace_flick_phase,
    slide_head_phase,
    slide_tail_phase,
    slide_tail_flick_phase,
    damage_phase,
)
