from sonolus.script.instruction import (
    StandardInstruction,
    StandardInstructionIcon,
    instruction_icons,
    instructions,
)


@instructions
class Instructions:
    tap: StandardInstruction.TAP
    tap_flick: StandardInstruction.TAP_FLICK
    tap_hold: StandardInstruction.TAP_HOLD
    hold_follow: StandardInstruction.HOLD_FOLLOW
    hold: StandardInstruction.HOLD
    hold_flick: StandardInstruction.FLICK
    avoid: StandardInstruction.AVOID


@instruction_icons
class InstructionIcons:
    hand: StandardInstructionIcon.HAND
