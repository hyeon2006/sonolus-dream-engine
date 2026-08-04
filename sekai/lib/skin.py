from __future__ import annotations

from enum import IntEnum
from typing import Self, assert_never

from sonolus.script.globals import level_data
from sonolus.script.interval import clamp
from sonolus.script.record import Record
from sonolus.script.sprite import (
    RenderMode,
    Sprite,
    SpriteGroup,
    StandardSprite,
    skin,
    sprite,
    sprite_group,
)


@skin
class BaseSkin:
    render_mode: RenderMode = RenderMode.LIGHTWEIGHT

    cover: StandardSprite.STAGE_COVER

    lane: StandardSprite.LANE
    stage_middle: StandardSprite.STAGE_MIDDLE
    judgment_line: StandardSprite.JUDGMENT_LINE
    stage_left_border: StandardSprite.STAGE_LEFT_BORDER
    stage_right_border: StandardSprite.STAGE_RIGHT_BORDER

    holodori_stage: Sprite = sprite("Holodori Stage")
    holodori_stage_background: Sprite = sprite("Holodori Stage Background")
    holodori_stage_judgment_line: Sprite = sprite("Holodori Stage Judgment Line")

    sim_line: StandardSprite.SIMULTANEOUS_CONNECTION_NEUTRAL
    measure_line: Sprite = sprite("Holodori Measure Line")
    skill_activation_line: Sprite = sprite("Holodori Skill Activation Line")

    note_icon: Sprite = sprite("Holodori Note Icon")

    note_normal_left: Sprite = sprite("Holodori Normal Note Left")
    note_normal_middle: Sprite = sprite("Holodori Normal Note Middle")
    note_normal_right: Sprite = sprite("Holodori Normal Note Right")
    note_normal_fallback: StandardSprite.NOTE_HEAD_CYAN

    note_offbeat_left: Sprite = sprite("Holodori Offbeat Note Left")
    note_offbeat_middle: Sprite = sprite("Holodori Offbeat Note Middle")
    note_offbeat_right: Sprite = sprite("Holodori Offbeat Note Right")
    note_offbeat_fallback: StandardSprite.NOTE_HEAD_CYAN

    note_long_left: Sprite = sprite("Holodori Long Note Left")
    note_long_middle: Sprite = sprite("Holodori Long Note Middle")
    note_long_right: Sprite = sprite("Holodori Long Note Right")
    note_long_fallback: StandardSprite.NOTE_HEAD_GREEN

    note_flick_left: Sprite = sprite("Holodori Flick Note Left")
    note_flick_middle: Sprite = sprite("Holodori Flick Note Middle")
    note_flick_right: Sprite = sprite("Holodori Flick Note Right")
    note_flick_fallback: StandardSprite.NOTE_HEAD_RED

    note_accent_left: Sprite = sprite("Holodori Accent Note Left")
    note_accent_middle: Sprite = sprite("Holodori Accent Note Middle")
    note_accent_right: Sprite = sprite("Holodori Accent Note Right")
    note_accent_fallback: StandardSprite.NOTE_HEAD_YELLOW

    long_relay_note: Sprite = sprite("Holodori Normal Relay")
    long_relay_note_fallback: StandardSprite.NOTE_TICK_GREEN

    long_accent_relay_note: Sprite = sprite("Holodori Accent Relay")
    long_accent_relay_note_fallback: StandardSprite.NOTE_TICK_YELLOW

    connection_long_normal: Sprite = sprite("Holodori Long Normal")
    connection_long_normal_fallback: StandardSprite.NOTE_CONNECTION_GREEN_SEAMLESS

    connection_long_accent: Sprite = sprite("Holodori Long Accent")
    connection_long_accent_fallback: StandardSprite.NOTE_CONNECTION_YELLOW_SEAMLESS

    slot_normal: Sprite = sprite("Holodori Slot Normal")
    slot_slide: Sprite = sprite("Holodori Slot Long")
    slot_flick: Sprite = sprite("Holodori Slot Flick")
    slot_accent: Sprite = sprite("Holodori Slot Accent")

    slot_glow_normal: Sprite = sprite("Holodori Slot Glow Normal")
    slot_glow_slide: Sprite = sprite("Holodori Slot Glow Long")
    slot_glow_flick: Sprite = sprite("Holodori Slot Glow Flick")
    slot_glow_accent: Sprite = sprite("Holodori Slot Glow Accent")

    flick_arrow_: SpriteGroup = sprite_group(f"Holodori Flick Arrow {i}" for i in range(1, 7))
    flick_arrow_fallback: StandardSprite.DIRECTIONAL_MARKER_RED

    flick_arrow_accent: SpriteGroup = sprite_group(f"Holodori Flick Arrow Accent {i}" for i in range(1, 7))
    flick_arrow_accent_fallback: StandardSprite.DIRECTIONAL_MARKER_YELLOW

    damage_note_left: Sprite = sprite("Holodori Damage Note Left")
    damage_note_middle: Sprite = sprite("Holodori Damage Note Middle")
    damage_note_right: Sprite = sprite("Holodori Damage Note Right")
    damage_note_basic: Sprite = sprite("Holodori Damage Note Basic")

    guide_green: Sprite = sprite("Holodori Guide Green")
    guide_green_fallback: StandardSprite.NOTE_CONNECTION_GREEN_SEAMLESS
    guide_yellow: Sprite = sprite("Holodori Guide Yellow")
    guide_yellow_fallback: StandardSprite.NOTE_CONNECTION_YELLOW_SEAMLESS
    guide_red: Sprite = sprite("Holodori Guide Red")
    guide_red_fallback: StandardSprite.NOTE_CONNECTION_RED_SEAMLESS
    guide_magenta: Sprite = sprite("Holodori Guide Magenta")
    guide_magenta_fallback: StandardSprite.NOTE_CONNECTION_PURPLE_SEAMLESS
    guide_cyan: Sprite = sprite("Holodori Guide Cyan")
    guide_cyan_fallback: StandardSprite.NOTE_CONNECTION_CYAN_SEAMLESS
    guide_blue: Sprite = sprite("Holodori Guide Blue")
    guide_blue_fallback: StandardSprite.NOTE_CONNECTION_BLUE_SEAMLESS
    guide_neutral: Sprite = sprite("Holodori Guide Neutral")
    guide_neutral_fallback: StandardSprite.NOTE_CONNECTION_NEUTRAL_SEAMLESS
    guide_black: Sprite = sprite("Holodori Guide Black")
    guide_black_fallback: StandardSprite.NOTE_CONNECTION_NEUTRAL_SEAMLESS

    beat_line: StandardSprite.GRID_NEUTRAL
    preview_divider: StandardSprite.GRID_NEUTRAL
    bpm_change_line: StandardSprite.GRID_PURPLE
    timescale_change_line: StandardSprite.GRID_YELLOW


EMPTY_SPRITE = Sprite(-1)
EMPTY_SPRITE_GROUP = SpriteGroup(-1, 1)


def first_available_sprite(*sprites: Sprite) -> Sprite:
    result = +EMPTY_SPRITE
    for s in sprites:
        if s.is_available:
            result @= s
            break
    return result


def first_available_sprite_group(*groups: SpriteGroup) -> SpriteGroup:
    result = +EMPTY_SPRITE_GROUP
    for g in groups:
        if g[0].is_available:
            result @= g
            break
    return result


class JudgmentSpriteSet(Record):
    judgment_background: Sprite
    judgment_gradient: Sprite
    judgment_edge: Sprite
    judgment_edge_left: Sprite
    judgment_center: Sprite


class BodyRenderType(IntEnum):
    NORMAL = 0
    SLIM = 1
    NORMAL_FALLBACK = 2
    SLIM_FALLBACK = 3


class BodySpriteSet(Record):
    render_type: BodyRenderType
    left: Sprite
    middle: Sprite
    right: Sprite

    @property
    def available(self):
        return self.middle.is_available

    @classmethod
    def of_normal(cls, left: Sprite, middle: Sprite, right: Sprite) -> Self:
        return cls(
            render_type=BodyRenderType.NORMAL,
            left=left,
            middle=middle,
            right=right,
        )

    @classmethod
    def of_slim(cls, left: Sprite, middle: Sprite, right: Sprite) -> Self:
        return cls(
            render_type=BodyRenderType.SLIM,
            left=left,
            middle=middle,
            right=right,
        )

    @classmethod
    def of_normal_fallback(cls, fallback: Sprite) -> Self:
        return cls(
            render_type=BodyRenderType.NORMAL_FALLBACK,
            left=EMPTY_SPRITE,
            middle=fallback,
            right=EMPTY_SPRITE,
        )

    @classmethod
    def of_slim_fallback(cls, fallback: Sprite) -> Self:
        return cls(
            render_type=BodyRenderType.SLIM_FALLBACK,
            left=EMPTY_SPRITE,
            middle=fallback,
            right=EMPTY_SPRITE,
        )


EMPTY_BODY_SPRITE_SET = BodySpriteSet(
    render_type=BodyRenderType.NORMAL_FALLBACK,
    left=EMPTY_SPRITE,
    middle=EMPTY_SPRITE,
    right=EMPTY_SPRITE,
)


def first_available_body_sprite_set(*sets: BodySpriteSet) -> BodySpriteSet:
    result = +EMPTY_BODY_SPRITE_SET
    for s in sets:
        if s.available:
            result @= s
            break
    return result


class ArrowRenderType(IntEnum):
    NORMAL = 0
    FALLBACK = 1


class ArrowSpriteSet(Record):
    render_type: ArrowRenderType
    up: SpriteGroup

    def _get_index_from_size(self, size: float) -> int:
        return int(clamp(round(size * 2), 1, 6)) - 1

    def get_sprite(self, size: float) -> Sprite:
        result = +Sprite
        match self.render_type:
            case ArrowRenderType.NORMAL:
                index = self._get_index_from_size(size)
                result @= self.up[index]
            case ArrowRenderType.FALLBACK:
                result @= self.up[0]
            case _:
                assert_never(self.render_type)
        return result

    @property
    def available(self):
        return self.up[0].is_available

    @classmethod
    def of_normal(cls, up: SpriteGroup) -> Self:
        return cls(
            render_type=ArrowRenderType.NORMAL,
            up=up,
        )

    @classmethod
    def of_fallback(cls, fallback: Sprite) -> Self:
        return cls(
            render_type=ArrowRenderType.FALLBACK,
            up=SpriteGroup(fallback.id, 1),
        )


def first_available_arrow_sprite_set(*sets: ArrowSpriteSet) -> ArrowSpriteSet:
    result = +EMPTY_ARROW_SPRITE_SET
    for s in sets:
        if s.available:
            result @= s
            break
    return result


EMPTY_ARROW_SPRITE_SET = ArrowSpriteSet(
    render_type=ArrowRenderType.FALLBACK,
    up=EMPTY_SPRITE_GROUP,
)


class NoteSpriteSet(Record):
    body: BodySpriteSet
    arrow: ArrowSpriteSet
    tick: Sprite
    slot: Sprite
    slot_glow: Sprite


EMPTY_NOTE_SPRITE_SET = NoteSpriteSet(
    body=EMPTY_BODY_SPRITE_SET,
    arrow=EMPTY_ARROW_SPRITE_SET,
    tick=EMPTY_SPRITE,
    slot=EMPTY_SPRITE,
    slot_glow=EMPTY_SPRITE,
)


class ActiveConnectorSpriteSet(Record):
    connection: Sprite
    slot_glow: Sprite


normal_note_body_sprites = BodySpriteSet.of_normal(
    left=BaseSkin.note_normal_left,
    middle=BaseSkin.note_normal_middle,
    right=BaseSkin.note_normal_right,
)
normal_note_fallback_body_sprites = BodySpriteSet.of_normal_fallback(
    fallback=BaseSkin.note_normal_fallback,
)
offbeat_note_body_sprites = BodySpriteSet.of_normal(
    left=BaseSkin.note_offbeat_left,
    middle=BaseSkin.note_offbeat_middle,
    right=BaseSkin.note_offbeat_right,
)
offbeat_note_fallback_body_sprites = BodySpriteSet.of_normal_fallback(
    fallback=BaseSkin.note_offbeat_fallback,
)
long_note_body_sprites = BodySpriteSet.of_normal(
    left=BaseSkin.note_long_left,
    middle=BaseSkin.note_long_middle,
    right=BaseSkin.note_long_right,
)
long_note_fallback_body_sprites = BodySpriteSet.of_normal_fallback(
    fallback=BaseSkin.note_long_fallback,
)
flick_note_body_sprites = BodySpriteSet.of_normal(
    left=BaseSkin.note_flick_left,
    middle=BaseSkin.note_flick_middle,
    right=BaseSkin.note_flick_right,
)
flick_note_fallback_body_sprites = BodySpriteSet.of_normal_fallback(
    fallback=BaseSkin.note_flick_fallback,
)
accent_note_body_sprites = BodySpriteSet.of_normal(
    left=BaseSkin.note_accent_left,
    middle=BaseSkin.note_accent_middle,
    right=BaseSkin.note_accent_right,
)
accent_note_fallback_body_sprites = BodySpriteSet.of_normal_fallback(
    fallback=BaseSkin.note_accent_fallback,
)
flick_arrow_sprites = ArrowSpriteSet.of_normal(
    up=BaseSkin.flick_arrow_,
)
flick_arrow_fallback_sprites = ArrowSpriteSet.of_fallback(
    fallback=BaseSkin.flick_arrow_fallback,
)
accent_flick_arrow_sprites = ArrowSpriteSet.of_normal(
    up=BaseSkin.flick_arrow_accent,
)
accent_flick_arrow_fallback_sprites = ArrowSpriteSet.of_fallback(
    fallback=BaseSkin.flick_arrow_accent_fallback,
)

damage_note_body_sprites = BodySpriteSet.of_normal(
    left=BaseSkin.damage_note_left,
    middle=BaseSkin.damage_note_middle,
    right=BaseSkin.damage_note_right,
)
damage_note_fallback_body_sprites = BodySpriteSet.of_normal_fallback(
    fallback=BaseSkin.damage_note_basic,
)


@level_data
class ActiveSkin:
    cover: Sprite

    lane: Sprite
    judgment_line: Sprite
    stage_left_border: Sprite
    stage_right_border: Sprite

    lane_background: Sprite
    lane_divider: Sprite
    stage_border: Sprite
    lane_background_preview: Sprite
    lane_divider_preview: Sprite
    stage_border_preview: Sprite

    judgment_neutral: JudgmentSpriteSet
    judgment_red: JudgmentSpriteSet
    judgment_green: JudgmentSpriteSet
    judgment_blue: JudgmentSpriteSet
    judgment_yellow: JudgmentSpriteSet
    judgment_purple: JudgmentSpriteSet
    judgment_cyan: JudgmentSpriteSet
    judgment_black: JudgmentSpriteSet

    holodori_stage: Sprite
    holodori_stage_background: Sprite
    holodori_stage_judgment_line: Sprite

    sim_line: Sprite
    measure_line: Sprite
    skill_activation_line: Sprite

    note_icon: Sprite

    normal_note: NoteSpriteSet
    offbeat_note: NoteSpriteSet
    slide_note: NoteSpriteSet
    flick_note: NoteSpriteSet
    critical_note: NoteSpriteSet
    critical_slide_note: NoteSpriteSet
    critical_flick_note: NoteSpriteSet
    trace_note: NoteSpriteSet
    trace_flick_note: NoteSpriteSet
    critical_trace_note: NoteSpriteSet
    critical_trace_flick_note: NoteSpriteSet
    normal_slide_tick_note: NoteSpriteSet
    critical_slide_tick_note: NoteSpriteSet
    damage_note: NoteSpriteSet

    active_slide_connector: ActiveConnectorSpriteSet
    critical_active_slide_connector: ActiveConnectorSpriteSet

    guide_green: Sprite
    guide_yellow: Sprite
    guide_red: Sprite
    guide_purple: Sprite
    guide_cyan: Sprite
    guide_blue: Sprite
    guide_neutral: Sprite
    guide_black: Sprite

    beat_line: Sprite
    preview_divider: Sprite
    bpm_change_line: Sprite
    timescale_change_line: Sprite


def init_skin():
    ActiveSkin.cover = BaseSkin.cover

    ActiveSkin.lane = BaseSkin.lane
    ActiveSkin.judgment_line = BaseSkin.judgment_line
    ActiveSkin.stage_left_border = BaseSkin.stage_left_border
    ActiveSkin.stage_right_border = BaseSkin.stage_right_border

    ActiveSkin.holodori_stage = BaseSkin.holodori_stage
    ActiveSkin.holodori_stage_background = BaseSkin.holodori_stage_background
    ActiveSkin.holodori_stage_judgment_line = BaseSkin.holodori_stage_judgment_line

    ActiveSkin.sim_line = BaseSkin.sim_line
    ActiveSkin.measure_line = first_available_sprite(BaseSkin.measure_line, BaseSkin.sim_line)
    ActiveSkin.skill_activation_line = first_available_sprite(BaseSkin.skill_activation_line, BaseSkin.sim_line)

    ActiveSkin.note_icon = BaseSkin.note_icon

    ActiveSkin.normal_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            normal_note_body_sprites,
            normal_note_fallback_body_sprites,
        ),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=BaseSkin.slot_normal,
        slot_glow=BaseSkin.slot_glow_normal,
    )
    ActiveSkin.offbeat_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            offbeat_note_body_sprites,
            offbeat_note_fallback_body_sprites,
        ),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=BaseSkin.slot_normal,
        slot_glow=BaseSkin.slot_glow_normal,
    )
    ActiveSkin.slide_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            long_note_body_sprites,
            long_note_fallback_body_sprites,
        ),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=BaseSkin.slot_slide,
        slot_glow=BaseSkin.slot_glow_slide,
    )
    ActiveSkin.flick_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            flick_note_body_sprites,
            flick_note_fallback_body_sprites,
        ),
        arrow=first_available_arrow_sprite_set(
            flick_arrow_sprites,
            flick_arrow_fallback_sprites,
        ),
        tick=EMPTY_SPRITE,
        slot=BaseSkin.slot_flick,
        slot_glow=BaseSkin.slot_glow_flick,
    )
    ActiveSkin.critical_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            accent_note_body_sprites,
            accent_note_fallback_body_sprites,
        ),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=BaseSkin.slot_accent,
        slot_glow=BaseSkin.slot_glow_accent,
    )
    ActiveSkin.critical_slide_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            accent_note_body_sprites,
            accent_note_fallback_body_sprites,
        ),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=BaseSkin.slot_accent,
        slot_glow=BaseSkin.slot_glow_accent,
    )
    ActiveSkin.critical_flick_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            accent_note_body_sprites,
            accent_note_fallback_body_sprites,
        ),
        arrow=first_available_arrow_sprite_set(
            accent_flick_arrow_sprites,
            accent_flick_arrow_fallback_sprites,
        ),
        tick=EMPTY_SPRITE,
        slot=BaseSkin.slot_accent,
        slot_glow=BaseSkin.slot_glow_accent,
    )
    ActiveSkin.trace_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            long_note_body_sprites,
            long_note_fallback_body_sprites,
        ),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=EMPTY_SPRITE,
        slot_glow=EMPTY_SPRITE,
    )
    ActiveSkin.trace_flick_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            flick_note_body_sprites,
            flick_note_fallback_body_sprites,
        ),
        arrow=first_available_arrow_sprite_set(
            flick_arrow_sprites,
            flick_arrow_fallback_sprites,
        ),
        tick=EMPTY_SPRITE,
        slot=EMPTY_SPRITE,
        slot_glow=EMPTY_SPRITE,
    )
    ActiveSkin.critical_trace_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            accent_note_body_sprites,
            accent_note_fallback_body_sprites,
        ),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=EMPTY_SPRITE,
        slot_glow=EMPTY_SPRITE,
    )
    ActiveSkin.critical_trace_flick_note = NoteSpriteSet(
        body=first_available_body_sprite_set(
            accent_note_body_sprites,
            accent_note_fallback_body_sprites,
        ),
        arrow=first_available_arrow_sprite_set(
            accent_flick_arrow_sprites,
            accent_flick_arrow_fallback_sprites,
        ),
        tick=EMPTY_SPRITE,
        slot=EMPTY_SPRITE,
        slot_glow=EMPTY_SPRITE,
    )
    ActiveSkin.normal_slide_tick_note = NoteSpriteSet(
        body=EMPTY_BODY_SPRITE_SET,
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=first_available_sprite(BaseSkin.long_relay_note, BaseSkin.long_relay_note_fallback),
        slot=EMPTY_SPRITE,
        slot_glow=EMPTY_SPRITE,
    )
    ActiveSkin.critical_slide_tick_note = NoteSpriteSet(
        body=EMPTY_BODY_SPRITE_SET,
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=first_available_sprite(BaseSkin.long_accent_relay_note, BaseSkin.long_accent_relay_note_fallback),
        slot=EMPTY_SPRITE,
        slot_glow=EMPTY_SPRITE,
    )
    ActiveSkin.damage_note = NoteSpriteSet(
        body=first_available_body_sprite_set(damage_note_body_sprites, damage_note_fallback_body_sprites),
        arrow=EMPTY_ARROW_SPRITE_SET,
        tick=EMPTY_SPRITE,
        slot=EMPTY_SPRITE,
        slot_glow=EMPTY_SPRITE,
    )

    ActiveSkin.active_slide_connector = ActiveConnectorSpriteSet(
        connection=first_available_sprite(
            BaseSkin.connection_long_normal,
            BaseSkin.connection_long_normal_fallback,
        ),
        slot_glow=BaseSkin.slot_glow_slide,
    )
    ActiveSkin.critical_active_slide_connector = ActiveConnectorSpriteSet(
        connection=first_available_sprite(
            BaseSkin.connection_long_accent,
            BaseSkin.connection_long_accent_fallback,
        ),
        slot_glow=BaseSkin.slot_glow_accent,
    )

    ActiveSkin.guide_green = first_available_sprite(
        BaseSkin.guide_green,
        BaseSkin.guide_green_fallback,
    )
    ActiveSkin.guide_yellow = first_available_sprite(
        BaseSkin.guide_yellow,
        BaseSkin.guide_yellow_fallback,
    )
    ActiveSkin.guide_red = first_available_sprite(
        BaseSkin.guide_red,
        BaseSkin.guide_red_fallback,
    )
    ActiveSkin.guide_purple = first_available_sprite(
        BaseSkin.guide_magenta,
        BaseSkin.guide_magenta_fallback,
    )
    ActiveSkin.guide_cyan = first_available_sprite(
        BaseSkin.guide_cyan,
        BaseSkin.guide_cyan_fallback,
    )
    ActiveSkin.guide_blue = first_available_sprite(
        BaseSkin.guide_blue,
        BaseSkin.guide_blue_fallback,
    )
    ActiveSkin.guide_neutral = first_available_sprite(
        BaseSkin.guide_neutral,
        BaseSkin.guide_neutral_fallback,
    )
    ActiveSkin.guide_black = first_available_sprite(
        BaseSkin.guide_black,
        BaseSkin.guide_black_fallback,
    )

    ActiveSkin.beat_line = BaseSkin.beat_line
    ActiveSkin.preview_divider = BaseSkin.preview_divider
    ActiveSkin.bpm_change_line = BaseSkin.bpm_change_line
    ActiveSkin.timescale_change_line = BaseSkin.timescale_change_line
