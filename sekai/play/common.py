from sonolus.script.globals import level_memory

EMPTY_TAP_SFX_SUPPRESSION_DURATION = 1.0


@level_memory
class PlayLevelMemory:
    last_flick_sfx_time: float


def init_play_common():
    PlayLevelMemory.last_flick_sfx_time = -1e8
