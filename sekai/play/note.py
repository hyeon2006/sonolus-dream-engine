from __future__ import annotations

from typing import assert_never, cast

from sonolus.script.archetype import (
    AnyArchetype,
    EntityRef,
    PlayArchetype,
    StandardImport,
    entity_data,
    entity_memory,
    exported,
    imported,
    shared_memory,
)
from sonolus.script.array import Dim
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.containers import VarArray
from sonolus.script.globals import level_memory
from sonolus.script.interval import Interval, lerp, remap_clamped, unlerp_clamped
from sonolus.script.quad import Quad
from sonolus.script.runtime import Touch, delta_time, input_offset, offset_adjusted_time, time, touches
from sonolus.script.timing import beat_to_time

from sekai.debug import DISABLE_NOTES
from sekai.lib import archetype_names
from sekai.lib.buckets import WINDOW_SCALE, SekaiWindow
from sekai.lib.connector import ActiveConnectorInfo, ConnectorKind
from sekai.lib.ease import EaseType, ease
from sekai.lib.layout import (
    IDENTITY_AFFINE_TRANSFORM,
    FlickDirection,
    Hitbox,
    Layout,
    compute_hitbox,
    progress_to,
    static_layout_transform,
)
from sekai.lib.note import (
    NoteKind,
    draw_hitbox_overlay,
    draw_note,
    get_attach_params,
    get_leniency,
    get_note_bucket,
    get_note_haptic_feedback,
    get_note_window,
    get_visual_spawn_time,
    has_tap_input,
    hitbox_draw_alpha,
    hitbox_draw_start,
    is_flick,
    is_head,
    map_note_kind,
    play_note_hit_effects,
    schedule_note_auto_sfx,
)
from sekai.lib.options import Options
from sekai.lib.timescale import (
    CompositeTime,
    group_hide_notes,
    group_preempt_time,
    group_scaled_time,
    group_time_to_scaled_time,
    update_timescale_group,
)
from sekai.play import input_manager
from sekai.play.common import PlayLevelMemory

DEFAULT_BEST_TOUCH_TIME = -1e8


class BaseNote(PlayArchetype):
    beat: StandardImport.BEAT
    timescale_group: StandardImport.TIMESCALE_GROUP
    lane: float = imported()
    size: float = imported()
    direction: FlickDirection = imported()
    active_head_ref: EntityRef[BaseNote] = imported(name="activeHead")
    is_attached: bool = imported(name="isAttached")
    connector_ease: EaseType = imported(name="connectorEase")
    segment_kind: ConnectorKind = imported(name="segmentKind")
    segment_red: float = imported(name="segmentRed", default=-1.0)
    segment_green: float = imported(name="segmentGreen", default=-1.0)
    segment_blue: float = imported(name="segmentBlue", default=-1.0)
    segment_alpha: float = imported(name="segmentAlpha")
    attach_head_ref: EntityRef[BaseNote] = imported(name="attachHead")
    attach_tail_ref: EntityRef[BaseNote] = imported(name="attachTail")
    next_ref: EntityRef[BaseNote] = imported(name="next")
    prev_ref: EntityRef[BaseNote] = imported(name="prev")
    kind: NoteKind = entity_data()
    data_init_done: bool = entity_data()
    target_time: float = entity_data()
    visual_start_time: float = entity_data()
    start_time: float = entity_data()
    target_scaled_time: CompositeTime = entity_data()
    attach_eased_frac: float = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()

    # The id of the touch assigned to this tap note by the input manager.
    captured_touch_id: int = shared_memory()

    active_connector_info: ActiveConnectorInfo = shared_memory()

    # For trace early touches
    best_touch_time: float = entity_memory()

    should_play_hit_effects: bool = entity_memory()

    hitbox: Hitbox = shared_memory()

    end_time: float = exported()
    played_hit_effects: bool = exported()

    @property
    def judgment_window(self) -> SekaiWindow:
        return get_note_window(self.kind)

    def init_data(self):
        if self.data_init_done:
            return

        self.kind = map_note_kind(cast(NoteKind, self.key))

        self.data_init_done = True

        if Options.mirror:
            self.lane *= -1

        self.target_time = beat_to_time(self.beat)
        window = get_note_window(self.kind)
        self.input_interval = window.bad + self.target_time + input_offset()
        self.unadjusted_input_interval = window.bad + self.target_time

        if not self.is_attached:
            self.target_scaled_time = group_time_to_scaled_time(self.timescale_group, self.target_time)
            self.visual_start_time = get_visual_spawn_time(self.timescale_group, self.target_scaled_time)
            self.start_time = min(self.visual_start_time, self.input_interval.start)

        if self.next_ref.index > 0:
            self.next_ref.get().prev_ref = self.ref()

    def preprocess(self):
        if DISABLE_NOTES:
            return
        self.init_data()

        self.result.bucket = get_note_bucket(self.kind)

        self.best_touch_time = DEFAULT_BEST_TOUCH_TIME
        self.active_connector_info.last_active_time = DEFAULT_BEST_TOUCH_TIME

        if self.is_attached:
            attach_head = self.attach_head_ref.get()
            attach_tail = self.attach_tail_ref.get()
            attach_head.init_data()
            attach_tail.init_data()
            self.connector_ease = attach_head.connector_ease
            self.attach_eased_frac = ease(
                self.connector_ease, unlerp_clamped(attach_head.target_time, attach_tail.target_time, self.target_time)
            )
            lane, size = get_attach_params(
                ease_type=attach_head.connector_ease,
                head_lane=attach_head._basic_visual_lane_at(self.target_time),
                head_size=attach_head.size,
                head_target_time=attach_head.target_time,
                tail_lane=attach_tail._basic_visual_lane_at(self.target_time),
                tail_size=attach_tail.size,
                tail_target_time=attach_tail.target_time,
                target_time=self.target_time,
            )
            self.lane = lane
            self.size = size
            self.visual_start_time = min(attach_head.visual_start_time, attach_tail.visual_start_time)
            self.start_time = min(self.visual_start_time, self.input_interval.start)
        if self.is_scored:
            schedule_note_auto_sfx(self.kind, self.target_time)
            self.hitbox @= compute_hitbox(
                static_layout_transform(),
                self.lane,
                self.size,
                get_leniency(self.kind),
            )

    def spawn_order(self) -> float:
        if DISABLE_NOTES or self.kind == NoteKind.ANCHOR:
            return 1e8
        return self.start_time

    def should_spawn(self) -> bool:
        if DISABLE_NOTES or self.kind == NoteKind.ANCHOR:
            return False
        return time() >= self.start_time

    def update_sequential(self):
        if self.despawn:
            return

        update_timescale_group(self.timescale_group)

        if self.should_do_delayed_trigger():
            self.judge(self.best_touch_time)
            return
        if (
            self.is_scored
            and time() in self.input_interval
            and self.captured_touch_id == 0
            and has_tap_input(self.kind)
        ):
            NoteMemory.active_tap_input_notes.append(self.ref())

    def touch(self):
        if not self.is_scored:
            return
        if self.despawn:
            return
        if time() < self.input_interval.start:
            return
        kind = self.kind
        match kind:
            case NoteKind.NORM_TAP | NoteKind.CRIT_TAP | NoteKind.NORM_HEAD_TAP | NoteKind.CRIT_HEAD_TAP:
                self.handle_tap_input()
            case NoteKind.NORM_TAIL_TRACE | NoteKind.CRIT_TAIL_TRACE:
                self.handle_trace_input()
            case (
                NoteKind.NORM_TRACE_FLICK
                | NoteKind.CRIT_TRACE_FLICK
                | NoteKind.NORM_TAIL_FLICK
                | NoteKind.CRIT_TAIL_FLICK
            ):
                self.handle_trace_flick_input()
            case NoteKind.NORM_TICK | NoteKind.CRIT_TICK | NoteKind.HIDE_TICK:
                self.handle_tick_input()
            case NoteKind.DAMAGE:
                self.handle_damage_input()
            case NoteKind.ANCHOR:
                pass
            case _:
                assert_never(kind)

    def update_parallel(self):
        if self.despawn:
            return
        if not self.is_scored and time() >= self.target_time:
            self.despawn = True
            return
        if time() > self.input_interval.end:
            self.handle_late_miss()
            return
        self.draw_hitbox()
        if time() < self.visual_start_time:
            return
        if is_head(self.kind) and time() > self.target_time:
            return
        if group_hide_notes(self.timescale_group):
            return
        draw_note(
            self.kind,
            self.beat,
            self.visual_lane,
            self.size,
            self.visual_progress,
            self.target_time,
            transform=IDENTITY_AFFINE_TRANSFORM,
            note_alpha=1.0,
        )

    def draw_hitbox(self):
        if not Options.show_hitboxes or not self.is_scored:
            return
        draw_start = hitbox_draw_start(self.kind, self.unadjusted_input_interval.start, self.target_time)
        if draw_start <= offset_adjusted_time() <= self.unadjusted_input_interval.end:
            draw_hitbox_overlay(
                self.hitbox,
                self.kind,
                hitbox_draw_alpha(self.kind, draw_start, self.target_time, offset_adjusted_time()),
                time_to_target=self.target_time - offset_adjusted_time(),
            )

    def should_do_delayed_trigger(self) -> bool:
        # Don't trigger if the previous frame was before the target time.
        # This gives the regular touch handling a chance to trigger on time the first time we pass the target time.
        if offset_adjusted_time() - delta_time() <= self.target_time and time() < self.input_interval.end:
            return False

        # Don't trigger if we never had a touch recorded.
        if self.best_touch_time == DEFAULT_BEST_TOUCH_TIME:
            return False

        # If a new input could improve the judgment...
        if offset_adjusted_time() < self.target_time + (self.target_time - self.best_touch_time):
            # If we're still in the perfect window, wait for it to end.
            if offset_adjusted_time() < self.target_time + self.judgment_window.perfect.end:
                return False
            # Otherwise, see if there's any ongoing touches in the hitbox.
            for touch in touches():
                if not touch.ended and self.hitbox.bounds.contains_point(touch.position):
                    return False
            # If we're past the perfect window, and there are no ongoing touches in the hitbox, we can trigger to
            # avoid delaying the trigger by too long.
        return True

    def terminate(self):
        if self.should_play_hit_effects:
            # We do this here for parallelism, and to reduce compilation time.
            play_note_hit_effects(
                self.kind,
                self.visual_lane,
                self.size,
                self.result.judgment,
                y_offset=0.0,
                pivot_lane=0.0,
                half_offset=False,
                single_line=False,
                lane_particles=True,
                transform=IDENTITY_AFFINE_TRANSFORM,
            )
        if self.is_scored:
            self.result.haptic = get_note_haptic_feedback(self.kind, self.result.judgment)
        self.end_time = offset_adjusted_time()
        self.played_hit_effects = self.should_play_hit_effects

    def handle_tap_input(self):
        if time() > self.input_interval.end:
            return
        if self.captured_touch_id == 0:
            return
        touch = next(tap for tap in touches() if tap.id == self.captured_touch_id)
        self.judge(touch.start_time)

    def handle_trace_input(self):
        if time() > self.input_interval.end:
            return
        if self.should_do_delayed_trigger():
            return
        has_touch = False
        for touch in touches():
            if not self.check_touch_is_eligible_for_trace(touch):
                continue
            input_manager.disallow_empty(touch)
            has_touch = True
            # Keep going so we disallow empty on all touches that are in the hitbox.
        if not has_touch:
            return
        if offset_adjusted_time() >= self.target_time:
            if offset_adjusted_time() - delta_time() <= self.target_time <= offset_adjusted_time():
                self.complete()
            else:
                self.judge(offset_adjusted_time())
        else:
            self.best_touch_time = offset_adjusted_time()

    def handle_trace_flick_input(self):
        if time() > self.input_interval.end:
            return
        if self.should_do_delayed_trigger():
            return
        has_flick = False
        for touch in touches():
            if not self.check_touch_is_eligible_for_trace(touch):
                continue
            if not self.check_touch_is_eligible_for_trace_flick(touch):
                continue
            has_flick = True
        if not has_flick:
            return
        if offset_adjusted_time() >= self.target_time:
            if offset_adjusted_time() - delta_time() <= self.target_time <= offset_adjusted_time():
                self.complete()
            else:
                self.judge(offset_adjusted_time())
            return
        current_abs_error = abs(self.best_touch_time - self.target_time)
        incoming_abs_error = abs(offset_adjusted_time() - self.target_time)
        if incoming_abs_error < current_abs_error:
            self.best_touch_time = offset_adjusted_time()

    def handle_tick_input(self):
        has_touch = False
        for touch in touches():
            if not self.hitbox.bounds.contains_point(touch.position):
                continue
            input_manager.disallow_empty(touch)
            has_touch = True
        if has_touch:
            if offset_adjusted_time() >= self.target_time:
                self.complete()
            else:
                # Always judge as perfect accuracy for ticks if touched.
                self.best_touch_time = self.target_time

    def handle_damage_input(self):
        has_touch = False
        for touch in touches():
            if not self.hitbox.bounds.contains_point(touch.position):
                continue
            input_manager.disallow_empty(touch)
            has_touch = True
        if has_touch:
            self.fail_damage()
        else:
            self.complete_damage()

    def handle_late_miss(self):
        kind = self.kind
        match kind:
            case NoteKind.NORM_TICK | NoteKind.CRIT_TICK | NoteKind.HIDE_TICK:
                self.fail_late(0.125)
            case NoteKind.DAMAGE:
                self.complete_damage()
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
                self.fail_late()
            case NoteKind.ANCHOR:
                pass
            case _:
                assert_never(kind)

    def check_touch_is_eligible_for_trace(self, touch: Touch) -> bool:
        # Note that this does not check the time, since time may not be updated if the touch is stationary.
        return self.hitbox.bounds.contains_point(touch.position)

    def check_touch_is_eligible_for_trace_flick(self, touch: Touch) -> bool:
        return (
            touch.time >= self.unadjusted_input_interval.start
            and touch.speed >= Layout.flick_speed_threshold
            and (
                self.hitbox.bounds.contains_point(touch.position)
                or self.hitbox.bounds.contains_point(touch.prev_position)
            )
        )

    def judge(self, actual_time: float):
        judgment = self.judgment_window.judge(actual_time, self.target_time)
        error = self.judgment_window.good.clamp(actual_time - self.target_time)
        self.result.judgment = judgment
        self.result.accuracy = error
        if self.result.bucket.id != -1:
            self.result.bucket_value = error * WINDOW_SCALE
        self.despawn = True
        self.should_play_hit_effects = judgment != Judgment.MISS
        self.post_judge()

    def complete(self):
        self.result.judgment = Judgment.PERFECT
        self.result.accuracy = 0
        if self.result.bucket.id != -1:
            self.result.bucket_value = 0
        self.despawn = True
        self.should_play_hit_effects = True
        self.post_judge()

    def complete_damage(self):
        self.result.judgment = Judgment.PERFECT
        self.result.accuracy = 0
        if self.result.bucket.id != -1:
            self.result.bucket_value = 0
        self.despawn = True
        self.should_play_hit_effects = True
        # Ideally we'd call post_judge here, but this is called in update_parallel. Not a big deal.

    def fail_late(self, accuracy: float | None = None):
        if accuracy is None:
            accuracy = self.judgment_window.good.end
        self.result.judgment = Judgment.MISS
        self.result.accuracy = accuracy
        self.result.bucket = Bucket(-1)
        self.despawn = True

    def fail_damage(self):
        self.result.judgment = Judgment.MISS
        self.result.accuracy = 0.125
        self.despawn = True
        self.should_play_hit_effects = True
        self.post_judge()

    def post_judge(self):
        if self.should_play_hit_effects and is_flick(self.kind):
            PlayLevelMemory.last_flick_sfx_time = time()

    @property
    def progress(self) -> float:
        if self.is_attached:
            attach_head = self.attach_head_ref.get()
            attach_tail = self.attach_tail_ref.get()
            head_progress = (
                progress_to(
                    attach_head.target_scaled_time,
                    group_scaled_time(attach_head.timescale_group),
                    group_preempt_time(attach_head.timescale_group),
                )
                if time() < attach_head.target_time
                else 1.0
            )
            tail_progress = progress_to(
                attach_tail.target_scaled_time,
                group_scaled_time(attach_tail.timescale_group),
                group_preempt_time(attach_tail.timescale_group),
            )
            head_frac = (
                0.0
                if time() < attach_head.target_time
                else unlerp_clamped(attach_head.target_time, attach_tail.target_time, time())
            )
            tail_frac = 1.0
            frac = unlerp_clamped(attach_head.target_time, attach_tail.target_time, self.target_time)
            return remap_clamped(head_frac, tail_frac, head_progress, tail_progress, frac)
        else:
            return progress_to(
                self.target_scaled_time,
                group_scaled_time(self.timescale_group),
                group_preempt_time(self.timescale_group),
            )

    @property
    def visual_progress(self) -> float:
        return self.progress

    def _basic_visual_lane_at(self, t: float) -> float:
        return self.lane

    def visual_lane_at(self, t: float) -> float:
        if self.is_attached:
            head = self.attach_head_ref.get()
            tail = self.attach_tail_ref.get()
            return lerp(head._basic_visual_lane_at(t), tail._basic_visual_lane_at(t), self.attach_eased_frac)
        return self._basic_visual_lane_at(t)

    @property
    def visual_lane(self) -> float:
        return self.visual_lane_at(time())

    @property
    def head_ease_frac(self) -> float:
        if self.is_attached:
            return unlerp_clamped(
                self.attach_head_ref.get().target_time, self.attach_tail_ref.get().target_time, self.target_time
            )
        else:
            return 0.0

    @property
    def tail_ease_frac(self) -> float:
        if self.is_attached:
            return unlerp_clamped(
                self.attach_head_ref.get().target_time, self.attach_tail_ref.get().target_time, self.target_time
            )
        else:
            return 1.0

    @property
    def effective_attach_head(self) -> BaseNote:
        ref = +EntityRef[BaseNote]
        if self.is_attached:
            ref @= self.attach_head_ref
        else:
            ref @= self.ref()
        return ref.get()

    @property
    def effective_attach_tail(self) -> BaseNote:
        ref = +EntityRef[BaseNote]
        if self.is_attached:
            ref @= self.attach_tail_ref
        else:
            ref @= self.ref()
        return ref.get()


def compute_slide_input_bounds(ease_type: EaseType, head: BaseNote, tail: BaseNote, t: float, leniency: float) -> Quad:
    eff_head = head.effective_attach_head
    eff_tail = tail.effective_attach_tail
    input_lane, input_size = get_attach_params(
        ease_type=ease_type,
        head_lane=eff_head._basic_visual_lane_at(t),
        head_size=eff_head.size,
        head_target_time=eff_head.target_time,
        tail_lane=eff_tail._basic_visual_lane_at(t),
        tail_size=eff_tail.size,
        tail_target_time=eff_tail.target_time,
        target_time=t,
    )
    return compute_hitbox(
        static_layout_transform(),
        input_lane,
        input_size,
        leniency,
    ).bounds


@level_memory
class NoteMemory:
    active_tap_input_notes: VarArray[EntityRef[BaseNote], Dim[256]]


NormalTapNote = BaseNote.derive(archetype_names.NORMAL_TAP_NOTE, is_scored=True, key=NoteKind.NORM_TAP)
CriticalTapNote = BaseNote.derive(archetype_names.CRITICAL_TAP_NOTE, is_scored=True, key=NoteKind.CRIT_TAP)
NormalTraceFlickNote = BaseNote.derive(
    archetype_names.NORMAL_TRACE_FLICK_NOTE, is_scored=True, key=NoteKind.NORM_TRACE_FLICK
)
CriticalTraceFlickNote = BaseNote.derive(
    archetype_names.CRITICAL_TRACE_FLICK_NOTE, is_scored=True, key=NoteKind.CRIT_TRACE_FLICK
)
NormalHeadTapNote = BaseNote.derive(archetype_names.NORMAL_HEAD_TAP_NOTE, is_scored=True, key=NoteKind.NORM_HEAD_TAP)
CriticalHeadTapNote = BaseNote.derive(
    archetype_names.CRITICAL_HEAD_TAP_NOTE, is_scored=True, key=NoteKind.CRIT_HEAD_TAP
)
NormalTailFlickNote = BaseNote.derive(
    archetype_names.NORMAL_TAIL_FLICK_NOTE, is_scored=True, key=NoteKind.NORM_TAIL_FLICK
)
CriticalTailFlickNote = BaseNote.derive(
    archetype_names.CRITICAL_TAIL_FLICK_NOTE, is_scored=True, key=NoteKind.CRIT_TAIL_FLICK
)
NormalTailTraceNote = BaseNote.derive(
    archetype_names.NORMAL_TAIL_TRACE_NOTE, is_scored=True, key=NoteKind.NORM_TAIL_TRACE
)
CriticalTailTraceNote = BaseNote.derive(
    archetype_names.CRITICAL_TAIL_TRACE_NOTE, is_scored=True, key=NoteKind.CRIT_TAIL_TRACE
)
NormalTickNote = BaseNote.derive(archetype_names.NORMAL_TICK_NOTE, is_scored=True, key=NoteKind.NORM_TICK)
CriticalTickNote = BaseNote.derive(archetype_names.CRITICAL_TICK_NOTE, is_scored=True, key=NoteKind.CRIT_TICK)
DamageNote = BaseNote.derive(archetype_names.DAMAGE_NOTE, is_scored=True, key=NoteKind.DAMAGE)
AnchorNote = BaseNote.derive(archetype_names.ANCHOR_NOTE, is_scored=False, key=NoteKind.ANCHOR)
TransientHiddenTickNote = BaseNote.derive(
    archetype_names.TRANSIENT_HIDDEN_TICK_NOTE, is_scored=True, key=NoteKind.HIDE_TICK
)


NOTE_ARCHETYPES = (
    NormalTapNote,
    CriticalTapNote,
    NormalTraceFlickNote,
    CriticalTraceFlickNote,
    NormalHeadTapNote,
    CriticalHeadTapNote,
    NormalTailFlickNote,
    CriticalTailFlickNote,
    NormalTailTraceNote,
    CriticalTailTraceNote,
    NormalTickNote,
    CriticalTickNote,
    DamageNote,
    AnchorNote,
    TransientHiddenTickNote,
)


def derive_note_archetypes[T: type[AnyArchetype]](base: T) -> tuple[T, ...]:
    """Helper function to derive all note archetypes from a given base archetype for used in watch and preview."""
    return tuple(base.derive(str(a.name), is_scored=a.is_scored, key=a.key) for a in NOTE_ARCHETYPES)
