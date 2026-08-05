from enum import IntEnum

from sonolus.script.options import select_option, slider_option, toggle_option
from sonolus.script.text import StandardText

from sekai.lib.localization import localized_options


class VibrateMode(IntEnum):
    STRONG = 0
    MEDIUM = 1
    WEAK = 2
    DISABLED = 3


@localized_options
class Options:
    speed: float = slider_option(
        name=StandardText.SPEED,
        standard=True,
        advanced=True,
        default=1,
        min=0.5,
        max=2,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    note_speed: float = slider_option(
        name=StandardText.NOTE_SPEED,
        scope="Holodori",
        default=5,
        min=1,
        max=12,
        step=0.1,
    )
    stage_brightness: float = slider_option(
        name=StandardText.STAGE_ALPHA,
        scope="Holodori",
        default=30,
        min=0,
        max=100,
        step=10,
    )
    mirror: bool = toggle_option(
        name=StandardText.MIRROR,
        scope="Holodori",
        default=False,
    )
    judgment_line_position: int = slider_option(
        name=StandardText.JUDGELINE_POSITION,
        scope="Holodori",
        default=0,
        min=-10,
        max=20,
        step=1,
    )
    stage_cover: int = slider_option(
        name=StandardText.STAGE_COVER_VERTICAL,
        advanced=True,
        scope="Holodori",
        default=0,
        min=0,
        max=100,
        step=1,
    )
    hidden: int = slider_option(
        name=StandardText.HIDDEN,
        scope="Holodori",
        advanced=True,
        default=0,
        min=0,
        max=100,
        step=1,
    )
    vibrate_mode: VibrateMode = select_option(
        name="Vibration Mode",
        scope="Holodori",
        values=[
            "strong",
            "medium",
            "weak",
            "disabled",
        ],
        default=1,
    )
    sim_line_enabled: bool = toggle_option(
        name=StandardText.SIMLINE,
        scope="Holodori",
        default=True,
    )
    measure_line_enabled: bool = toggle_option(
        name="Enable Measure Line",
        scope="Holodori",
        default=True,
    )
    offbeat_note_enabled: bool = toggle_option(
        name="Enable Offbeat Note",
        scope="Holodori",
        default=True,
    )
    lane_effect_enabled: bool = toggle_option(
        name=StandardText.LANE_EFFECT,
        scope="Holodori",
        default=True,
    )
    sfx_enabled: bool = toggle_option(
        name=StandardText.EFFECT,
        scope="Holodori",
        default=True,
    )
    auto_sfx: bool = toggle_option(
        name=StandardText.EFFECT_AUTO,
        scope="Holodori",
        default=False,
    )
    note_effect_enabled: bool = toggle_option(
        name=StandardText.NOTE_EFFECT,
        scope="Holodori",
        default=True,
    )
    note_effect_size: float = slider_option(
        name=StandardText.NOTE_EFFECT_SIZE,
        scope="Holodori",
        default=1,
        min=0.1,
        max=2,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    slot_effect_enabled: bool = toggle_option(
        name=StandardText.SLOT_EFFECT,
        scope="Holodori",
        default=True,
    )
    slot_effect_size: float = slider_option(
        name=StandardText.SLOT_EFFECT_SIZE,
        scope="Holodori",
        default=1,
        min=0,
        max=2,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    lock_stage_aspect_ratio: bool = toggle_option(
        name=StandardText.STAGE_ASPECTRATIO_LOCK,
        scope="Holodori",
        default=True,
    )
    hide_ui: bool = toggle_option(
        name="Hide UI",
        scope="Holodori",
        default=False,
    )
    show_lane: bool = toggle_option(
        name=StandardText.STAGE,
        scope="Holodori",
        default=True,
    )
    slide_quality: float = slider_option(
        name="Slide Quality",
        scope="Holodori",
        default=1,
        min=0.5,
        max=2,
        step=0.1,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    guide_quality: float = slider_option(
        name="Guide Quality",
        scope="Holodori",
        default=1,
        min=0.5,
        max=2,
        step=0.1,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    note_margin: float = slider_option(
        name="Note Margin",
        scope="Holodori",
        default=0.0,
        min=0.0,
        max=0.2,
        step=0.01,
    )
    effect_animation_speed: float = slider_option(
        name="Effect Animation Speed",
        scope="Holodori",
        default=1,
        min=0.25,
        max=4,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    disable_timescale: bool = toggle_option(
        name="Disable Timescale",
        standard=True,
        advanced=True,
        default=False,
    )
    show_hitboxes: bool = toggle_option(
        name="Show Hitboxes",
        standard=True,
        advanced=True,
        scope="Holodori",
        default=False,
    )
    test_aspect_ratio: bool = toggle_option(
        name="Test Aspect Ratio",
        standard=True,
        advanced=True,
        scope="Holodori",
        default=False,
    )
