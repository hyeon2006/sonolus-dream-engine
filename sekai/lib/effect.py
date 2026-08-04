from sonolus.script.effect import Effect, StandardEffect, effect, effects

EMPTY_EFFECT = Effect(-1)


@effects
class Effects:
    stage: StandardEffect.STAGE

    normal_perfect: StandardEffect.PERFECT
    normal_great: StandardEffect.GREAT
    normal_good: StandardEffect.GOOD

    flick_perfect: StandardEffect.PERFECT_ALTERNATIVE

    normal_hold: StandardEffect.HOLD
    normal_tick: Effect = effect("Holodori Relay")

    critical_tap: Effect = effect("Holodori Accent Tap")
    critical_flick: Effect = effect("Holodori Accent Flick")
    critical_hold: Effect = effect("Holodori Accent Hold")
    critical_tick: Effect = effect("Holodori Accent Tick")


SFX_DISTANCE = 0.02


def first_available_effect(*args: Effect) -> Effect:
    result = +EMPTY_EFFECT
    for e in args:
        if e.is_available:
            result @= e
            break
    return result
