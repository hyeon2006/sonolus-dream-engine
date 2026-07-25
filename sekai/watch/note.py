from __future__ import annotations

from typing import cast

from sonolus.script.archetype import (
    EntityRef,
    StandardImport,
    WatchArchetype,
    entity_data,
    imported,
    shared_memory,
)
from sonolus.script.bucket import Judgment
from sonolus.script.interval import lerp, remap_clamped, unlerp_clamped
from sonolus.script.quad import Quad
from sonolus.script.runtime import is_replay, is_skip, time
from sonolus.script.timing import beat_to_time

from sekai.debug import DISABLE_NOTES
from sekai.lib.connector import ActiveConnectorInfo, ConnectorKind
from sekai.lib.ease import EaseType, ease
from sekai.lib.layout import (
    IDENTITY_AFFINE_TRANSFORM,
    FlickDirection,
    Hitbox,
    compute_hitbox,
    progress_to,
    static_layout_transform,
)
from sekai.lib.note import (
    NoteKind,
    damage_tick_input_start_beat,
    draw_hitbox_overlay,
    draw_note,
    get_attach_params,
    get_leniency,
    get_note_bucket,
    get_note_window,
    get_visual_spawn_time,
    hitbox_draw_alpha,
    hitbox_draw_start,
    is_head,
    map_note_kind,
    mirror_flick_direction,
    play_note_hit_effects,
    schedule_note_auto_sfx,
    schedule_note_sfx,
    schedule_note_slot_effects,
)
from sekai.lib.options import Options
from sekai.lib.timescale import (
    CompositeTime,
    group_force_note_speed,
    group_hide_notes,
    group_scaled_time,
    group_time_to_scaled_time,
    update_timescale_group,
)
from sekai.play.note import derive_note_archetypes


class WatchBaseNote(WatchArchetype):
    beat: StandardImport.BEAT
    timescale_group: StandardImport.TIMESCALE_GROUP
    lane: float = imported()
    size: float = imported()
    direction: FlickDirection = imported()
    active_head_ref: EntityRef[WatchBaseNote] = imported(name="activeHead")
    is_attached: bool = imported(name="isAttached")
    connector_ease: EaseType = imported(name="connectorEase")
    segment_kind: ConnectorKind = imported(name="segmentKind")
    segment_alpha: float = imported(name="segmentAlpha")
    attach_head_ref: EntityRef[WatchBaseNote] = imported(name="attachHead")
    attach_tail_ref: EntityRef[WatchBaseNote] = imported(name="attachTail")
    next_ref: EntityRef[WatchBaseNote] = imported(name="next")
    prev_ref: EntityRef[WatchBaseNote] = imported(name="prev")
    kind: NoteKind = entity_data()
    data_init_done: bool = entity_data()
    target_time: float = entity_data()
    visual_start_time: float = entity_data()
    start_time: float = entity_data()
    target_scaled_time: CompositeTime = entity_data()

    active_connector_info: ActiveConnectorInfo = shared_memory()

    hitbox: Hitbox = shared_memory()
    attach_eased_frac: float = shared_memory()

    end_time: float = imported()
    played_hit_effects: bool = imported()

    judgment: StandardImport.JUDGMENT = imported()
    accuracy: StandardImport.ACCURACY = imported()

    def init_data(self):
        if self.data_init_done:
            return

        self.kind = map_note_kind(cast(NoteKind, self.key))

        self.data_init_done = True

        if Options.mirror:
            self.lane *= -1
            self.direction = mirror_flick_direction(self.direction)

        self.target_time = beat_to_time(self.beat)

        if not self.is_attached:
            self.target_scaled_time = group_time_to_scaled_time(self.timescale_group, self.target_time)
            self.visual_start_time = get_visual_spawn_time(self.timescale_group, self.target_scaled_time)
            self.start_time = self.visual_start_time

        if self.next_ref.index > 0:
            self.next_ref.get().prev_ref = self.ref()

    def preprocess(self):
        if DISABLE_NOTES:
            self.result.target_time = 1e8
            return
        self.init_data()

        self.result.bucket = get_note_bucket(self.kind)

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
            self.start_time = self.visual_start_time
        if self.is_scored:
            self.hitbox @= compute_hitbox(
                static_layout_transform(),
                self.lane,
                self.size,
                get_leniency(self.kind),
            )

        if is_replay():
            if self.played_hit_effects:
                if Options.auto_sfx:
                    schedule_note_auto_sfx(self.kind, self.target_time)
                else:
                    schedule_note_sfx(self.kind, self.judgment, self.end_time)
                self.schedule_slot_effects_at(self.end_time)
            self.result.bucket_value = self.accuracy * 1000
        else:
            self.judgment = Judgment.PERFECT
            if self.is_scored:
                schedule_note_sfx(self.kind, Judgment.PERFECT, self.target_time)
                self.schedule_slot_effects_at(self.target_time)

        self.result.target_time = self.target_time

    def schedule_slot_effects_at(self, t: float):
        schedule_note_slot_effects(
            self.kind,
            self.visual_lane_at(t),
            self.size,
            t,
            self.direction,
            y_offset=0.0,
            pivot_lane=0.0,
            half_offset=False,
            single_line=False,
            transform=IDENTITY_AFFINE_TRANSFORM,
        )

    def spawn_time(self) -> float:
        if DISABLE_NOTES or self.kind == NoteKind.ANCHOR:
            return 1e8
        return self.start_time

    def despawn_time(self) -> float:
        if is_replay() and self.is_scored:
            if self.end_time == 0 and self.accuracy == 0 and self.judgment == Judgment.MISS:
                # This is a note that's part of a partial replay that ended before this note was hit
                return 1e8
            return self.end_time
        else:
            return self.target_time

    def update_sequential(self):
        update_timescale_group(self.timescale_group)

    def update_parallel(self):
        self.draw_hitbox()
        if time() < self.visual_start_time:
            return
        if is_head(self.kind) and time() > self.target_time:
            return
        if group_hide_notes(self.timescale_group):
            return
        if Options.disable_fake_notes and not self.is_scored:
            return
        draw_note(
            self.kind,
            self.visual_lane,
            self.size,
            self.visual_progress,
            self.direction,
            self.target_time,
            transform=IDENTITY_AFFINE_TRANSFORM,
            note_alpha=1.0,
        )

    def draw_hitbox(self):
        if not Options.show_hitboxes or not self.is_scored:
            return
        if self.kind == NoteKind.HIDE_DAMAGE_TICK:
            self.draw_damage_tick_hitbox()
            return
        input_interval = get_note_window(self.kind).bad + self.target_time
        draw_start = hitbox_draw_start(self.kind, input_interval.start, self.target_time)
        if draw_start <= time() <= input_interval.end:
            draw_hitbox_overlay(
                self.hitbox,
                self.kind,
                hitbox_draw_alpha(self.kind, draw_start, self.target_time, time()),
                time_to_target=self.target_time - time(),
            )

    def draw_damage_tick_hitbox(self):
        # Damage segments have no connector-level hold hitbox, so this is the only hitbox drawn for them.
        if self.active_head_ref.index <= 0:
            return
        window_start_beat = max(damage_tick_input_start_beat(self.beat), self.active_head_ref.get().beat)
        window_start_time = beat_to_time(window_start_beat)
        draw_start = hitbox_draw_start(self.kind, window_start_time, self.target_time)
        if draw_start <= time() <= self.target_time:
            hitbox = +Hitbox
            hitbox.bounds @= self.damage_tick_input_bounds(time())
            draw_hitbox_overlay(
                hitbox,
                self.kind,
                hitbox_draw_alpha(self.kind, draw_start, self.target_time, time()),
                time_to_target=self.target_time - time(),
            )

    def damage_tick_input_bounds(self, t: float) -> Quad:
        connection_head_ref = +EntityRef[WatchBaseNote]
        if self.is_attached:
            connection_head_ref @= self.attach_head_ref
        else:
            connection_head_ref @= self.ref()
        while connection_head_ref.get().prev_ref.index > 0 and connection_head_ref.get().target_time > t:
            connection_head_ref.index = connection_head_ref.get().prev_ref.index
        if connection_head_ref.get().next_ref.index <= 0 and connection_head_ref.get().prev_ref.index > 0:
            connection_head_ref.index = connection_head_ref.get().prev_ref.index
        connection_head = connection_head_ref.get()
        result = +Quad
        if connection_head.next_ref.index > 0:
            result @= compute_slide_input_bounds(
                connection_head.connector_ease,
                connection_head,
                connection_head.next_ref.get(),
                t,
                get_leniency(self.kind),
            )
        else:
            result @= self.hitbox.bounds
        return result

    def terminate(self):
        if is_skip():
            return
        if time() < self.despawn_time():
            return
        if (not is_replay() or self.played_hit_effects) and self.is_scored:
            play_note_hit_effects(
                self.kind,
                self.visual_lane,
                self.size,
                self.direction,
                self.judgment,
                y_offset=0.0,
                pivot_lane=0.0,
                half_offset=False,
                lane_particles=True,
                transform=IDENTITY_AFFINE_TRANSFORM,
            )

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
    def progress(self) -> float:
        if self.is_attached:
            attach_head = self.attach_head_ref.get()
            attach_tail = self.attach_tail_ref.get()
            head_progress = (
                progress_to(
                    attach_head.target_scaled_time,
                    group_scaled_time(attach_head.timescale_group),
                    group_force_note_speed(attach_head.timescale_group),
                )
                if time() < attach_head.target_time
                else 1.0
            )
            tail_progress = progress_to(
                attach_tail.target_scaled_time,
                group_scaled_time(attach_tail.timescale_group),
                group_force_note_speed(attach_tail.timescale_group),
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
                group_force_note_speed(self.timescale_group),
            )

    @property
    def visual_progress(self) -> float:
        return self.progress

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
    def effective_attach_head(self) -> WatchBaseNote:
        ref = +EntityRef[WatchBaseNote]
        if self.is_attached:
            ref @= self.attach_head_ref
        else:
            ref @= self.ref()
        return ref.get()

    @property
    def effective_attach_tail(self) -> WatchBaseNote:
        ref = +EntityRef[WatchBaseNote]
        if self.is_attached:
            ref @= self.attach_tail_ref
        else:
            ref @= self.ref()
        return ref.get()


def compute_slide_input_bounds(
    ease_type: EaseType, head: WatchBaseNote, tail: WatchBaseNote, t: float, leniency: float
) -> Quad:
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


WATCH_NOTE_ARCHETYPES = derive_note_archetypes(WatchBaseNote)
