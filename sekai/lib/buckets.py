from typing import Literal, assert_never

from sonolus.script.bucket import Bucket, Judgment, JudgmentWindow, bucket, bucket_sprite, buckets
from sonolus.script.interval import Interval
from sonolus.script.record import Record
from sonolus.script.sprite import Sprite
from sonolus.script.text import StandardText

from sekai.lib.skin import BaseSkin

WINDOW_SCALE = 1000  # Windows are in ms


def create_bucket_sprites(
    body: Sprite | None = None,
    body_fallback: Sprite | None = None,
    arrow: Sprite | None = None,
    tick: Sprite | None = None,
    tick_fallback: Sprite | None = None,
    connector: Sprite | None = None,
    connector_fallback: Sprite | None = None,
    body_pos: Literal["left", "middle", "right"] = "middle",
):
    sprites = []

    if body_pos == "left":
        connector_x = 0.5
        body_x = -2.0
    elif body_pos == "middle":
        connector_x = 0.0
        body_x = 0.0
    elif body_pos == "right":
        connector_x = -0.5
        body_x = 2.0
    else:
        assert_never(body_pos)

    if connector is not None:
        sprite_args = {
            "sprite": connector,
            "x": connector_x,
            "y": 0,
            "w": 2,
            "h": 5,
            "rotation": -90,
        }
        if connector_fallback is not None:
            sprite_args["fallback_sprite"] = connector_fallback
        sprites.append(bucket_sprite(**sprite_args))

    if body is not None:
        sprite_args = {
            "sprite": body,
            "x": body_x,
            "y": 0,
            "w": 2,
            "h": 2,
            "rotation": -90,
        }
        if body_fallback is not None:
            sprite_args["fallback_sprite"] = body_fallback
        sprites.append(bucket_sprite(**sprite_args))

    if arrow is not None:
        sprites.append(
            bucket_sprite(
                sprite=arrow,
                x=body_x + 1,
                y=0,
                w=2,
                h=2,
                rotation=-90,
            )
        )

    if tick is not None:
        sprite_args = {
            "sprite": tick,
            "x": body_x,
            "y": 0,
            "w": 2,
            "h": 2,
            "rotation": -90,
        }
        if tick_fallback is not None:
            sprite_args["fallback_sprite"] = tick_fallback
        sprites.append(bucket_sprite(**sprite_args))

    return sprites


@buckets
class Buckets:
    # Normal buckets
    normal_tap: Bucket = bucket(
        sprites=create_bucket_sprites(body=BaseSkin.normal_note_basic, body_fallback=BaseSkin.note_cyan_fallback),
        unit=StandardText.MILLISECOND_UNIT,
    )
    critical_tap: Bucket = bucket(
        sprites=create_bucket_sprites(body=BaseSkin.critical_note_basic, body_fallback=BaseSkin.note_yellow_fallback),
        unit=StandardText.MILLISECOND_UNIT,
    )

    normal_trace_flick: Bucket = bucket(
        sprites=create_bucket_sprites(
            body=BaseSkin.trace_flick_note_basic,
            body_fallback=BaseSkin.note_red_fallback,
            tick=BaseSkin.trace_flick_note_tick,
            tick_fallback=BaseSkin.trace_note_red_tick,
            arrow=BaseSkin.flick_arrow_red_fallback,
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )
    critical_trace_flick: Bucket = bucket(
        sprites=create_bucket_sprites(
            body=BaseSkin.critical_trace_flick_note_basic,
            body_fallback=BaseSkin.note_yellow_fallback,
            tick=BaseSkin.critical_trace_flick_note_tick,
            tick_fallback=BaseSkin.trace_note_yellow_tick,
            arrow=BaseSkin.flick_arrow_yellow_fallback,
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )

    # Head buckets
    normal_head_tap: Bucket = bucket(
        sprites=create_bucket_sprites(
            connector=BaseSkin.normal_active_slide_connection_normal,
            connector_fallback=BaseSkin.active_slide_connection_green_fallback,
            body=BaseSkin.slide_note_basic,
            body_fallback=BaseSkin.note_green_fallback,
            body_pos="left",
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )
    critical_head_tap: Bucket = bucket(
        sprites=create_bucket_sprites(
            connector=BaseSkin.critical_active_slide_connection_normal,
            connector_fallback=BaseSkin.active_slide_connection_yellow_fallback,
            body=BaseSkin.critical_note_basic,
            body_fallback=BaseSkin.note_yellow_fallback,
            body_pos="left",
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )

    # Tail buckets
    normal_tail_flick: Bucket = bucket(
        sprites=create_bucket_sprites(
            connector=BaseSkin.normal_active_slide_connection_normal,
            connector_fallback=BaseSkin.active_slide_connection_green_fallback,
            body=BaseSkin.flick_note_basic,
            body_fallback=BaseSkin.note_red_fallback,
            body_pos="right",
            arrow=BaseSkin.flick_arrow_red_fallback,
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )
    critical_tail_flick: Bucket = bucket(
        sprites=create_bucket_sprites(
            connector=BaseSkin.critical_active_slide_connection_normal,
            connector_fallback=BaseSkin.active_slide_connection_yellow_fallback,
            body=BaseSkin.critical_flick_note_basic,
            body_fallback=BaseSkin.note_yellow_fallback,
            body_pos="right",
            arrow=BaseSkin.flick_arrow_yellow_fallback,
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )
    normal_tail_trace: Bucket = bucket(
        sprites=create_bucket_sprites(
            connector=BaseSkin.normal_active_slide_connection_normal,
            connector_fallback=BaseSkin.active_slide_connection_green_fallback,
            body=BaseSkin.normal_trace_note_basic,
            body_fallback=BaseSkin.note_green_fallback,
            body_pos="right",
            tick=BaseSkin.normal_trace_note_tick,
            tick_fallback=BaseSkin.trace_note_green_tick,
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )
    critical_tail_trace: Bucket = bucket(
        sprites=create_bucket_sprites(
            connector=BaseSkin.critical_active_slide_connection_normal,
            connector_fallback=BaseSkin.active_slide_connection_yellow_fallback,
            body=BaseSkin.critical_trace_note_basic,
            body_fallback=BaseSkin.note_yellow_fallback,
            body_pos="right",
            tick=BaseSkin.critical_trace_note_tick,
            tick_fallback=BaseSkin.trace_note_yellow_tick,
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )


def init_buckets():
    Buckets.normal_tap.window @= TAP_WINDOW.bucket_window
    Buckets.critical_tap.window @= TAP_WINDOW.bucket_window
    Buckets.normal_trace_flick.window @= TRACE_FLICK_WINDOW.bucket_window
    Buckets.critical_trace_flick.window @= TRACE_FLICK_WINDOW.bucket_window
    Buckets.normal_head_tap.window @= TAP_WINDOW.bucket_window
    Buckets.critical_head_tap.window @= TAP_WINDOW.bucket_window
    Buckets.normal_tail_trace.window @= SLIDE_END_TRACE_WINDOW.bucket_window
    Buckets.critical_tail_trace.window @= SLIDE_END_TRACE_WINDOW.bucket_window
    Buckets.normal_tail_flick.window @= SLIDE_END_FLICK_WINDOW.bucket_window
    Buckets.critical_tail_flick.window @= SLIDE_END_FLICK_WINDOW.bucket_window


def round_interval(interval: Interval) -> Interval:
    return Interval(
        start=round(interval.start),
        end=round(interval.end),
    )


class SekaiWindow(Record):
    perfect: Interval
    great: Interval
    good: Interval
    bad: Interval

    @property
    def bucket_window(self):
        return JudgmentWindow(
            perfect=round_interval(self.perfect * WINDOW_SCALE),
            great=round_interval(self.great * WINDOW_SCALE),
            good=round_interval(self.good * WINDOW_SCALE),
        )

    def judge(self, actual: float, target: float) -> Judgment:
        diff = actual - target
        if diff in self.perfect:
            return Judgment.PERFECT
        elif diff in self.great:
            return Judgment.GREAT
        elif diff in self.good:
            return Judgment.GOOD
        else:
            return Judgment.MISS


def frames_to_window(
    perfect: float | tuple[float, float],
    great: float | tuple[float, float] | None,
    good: float | tuple[float, float] | None,
    bad: float | tuple[float, float] | None,  # Unused
) -> SekaiWindow:
    if great is None:
        great = perfect
    if good is None:
        good = great
    if bad is None:
        bad = good
    perfect = perfect if isinstance(perfect, tuple) else (perfect, perfect)
    great = great if isinstance(great, tuple) else (great, great)
    good = good if isinstance(good, tuple) else (good, good)
    bad = bad if isinstance(bad, tuple) else (bad, bad)
    return SekaiWindow(
        perfect=Interval(-perfect[0] / 60, perfect[1] / 60),
        great=Interval(-great[0] / 60, great[1] / 60),
        good=Interval(-good[0] / 60, good[1] / 60),
        bad=Interval(-bad[0] / 60, bad[1] / 60),
    )


TAP_WINDOW = frames_to_window((4, 3), (6, 5), (8, 7), (9, 8))

TRACE_FLICK_WINDOW = frames_to_window((6, 5), None, None, (9, 8))

SLIDE_END_TRACE_WINDOW = frames_to_window(1.5, None, None, None)
SLIDE_END_FLICK_WINDOW = frames_to_window((6, 5), None, None, (9, 8))

SLIDE_TICK_JUDGMENT_WINDOW = frames_to_window(1.5, None, None, None)

EMPTY_JUDGMENT_WINDOW = frames_to_window(0, None, None, None)
