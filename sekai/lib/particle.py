from sonolus.script.globals import level_data
from sonolus.script.particle import Particle, StandardParticle, particle, particles
from sonolus.script.record import Record


@particles
class BaseParticles:
    lane: StandardParticle.LANE_LINEAR

    normal_note_lane_linear: Particle = particle("Holodori Note Lane Linear")
    normal_slide_note_lane_linear: Particle = particle("Holodori Slide Lane Linear")
    normal_flick_note_lane_linear: Particle = particle("Holodori Flick Lane Linear")
    critical_note_lane_linear: Particle = particle("Holodori Critical Lane Linear")
    critical_slide_note_lane_linear: Particle = particle("Holodori Critical Slide Lane Linear")
    critical_flick_note_lane_linear: Particle = particle("Holodori Critical Flick Lane Linear")

    normal_note_circular: Particle = particle("Holodori Normal Note Circular")
    normal_note_linear: Particle = particle("Holodori Normal Note Linear")
    slot_normal_linear: Particle = particle("Holodori Slot Normal Linear")

    long_note_circular: Particle = particle("Holodori Long Note Circular")
    long_note_linear: Particle = particle("Holodori Long Note Linear")
    slot_long_linear: Particle = particle("Holodori Slot Long Linear")

    flick_note_circular: Particle = particle("Holodori Flick Note Circular")
    flick_note_linear: Particle = particle("Holodori Flick Note Linear")
    flick_note_directional: Particle = particle("Holodori Flick Note Directional")
    slot_flick_linear: Particle = particle("Holodori Slot Flick Linear")

    accent_note_circular: Particle = particle("Holodori Accent Note Circular")
    accent_note_linear: Particle = particle("Holodori Accent Note Linear")
    accent_note_directional: Particle = particle("Holodori Accent Note Directional")
    slot_accent_linear: Particle = particle("Holodori Slot Accent Linear")

    normal_relay: Particle = particle("Holodori Normal Relay")
    accent_relay: Particle = particle("Holodori Accent Relay")

    long_normal_circular: Particle = particle("Holodori Long Normal Circular")
    long_normal_linear: Particle = particle("Holodori Long Normal Linear")
    long_normal_trail_linear: Particle = particle("Holodori Long Normal Trail Linear")
    long_normal_slot_linear: Particle = particle("Holodori Long Normal Slot Linear")

    long_accent_circular: Particle = particle("Holodori Long Accent Circular")
    long_accent_linear: Particle = particle("Holodori Long Accent Linear")
    long_accent_trail_linear: Particle = particle("Holodori Long Accent Trail Linear")
    long_accent_slot_linear: Particle = particle("Holodori Long Accent Slot Linear")

    damage_note_circular: Particle = particle("Holodori Damage Note Circular")
    damage_note_linear: Particle = particle("Holodori Damage Note Linear")

    normal_note_circular_fallback: StandardParticle.NOTE_CIRCULAR_TAP_CYAN
    normal_note_linear_fallback: StandardParticle.NOTE_LINEAR_TAP_CYAN
    long_note_circular_fallback: StandardParticle.NOTE_CIRCULAR_TAP_GREEN
    long_note_linear_fallback: StandardParticle.NOTE_LINEAR_TAP_GREEN
    flick_note_circular_fallback: StandardParticle.NOTE_CIRCULAR_TAP_RED
    flick_note_linear_fallback: StandardParticle.NOTE_LINEAR_TAP_RED
    flick_note_directional_fallback: StandardParticle.NOTE_LINEAR_ALTERNATIVE_RED
    accent_note_circular_fallback: StandardParticle.NOTE_CIRCULAR_TAP_YELLOW
    accent_note_linear_fallback: StandardParticle.NOTE_LINEAR_TAP_YELLOW
    accent_note_directional_fallback: StandardParticle.NOTE_LINEAR_ALTERNATIVE_YELLOW
    normal_relay_fallback: StandardParticle.NOTE_CIRCULAR_ALTERNATIVE_GREEN
    accent_relay_fallback: StandardParticle.NOTE_CIRCULAR_ALTERNATIVE_YELLOW
    long_normal_circular_fallback: StandardParticle.NOTE_CIRCULAR_HOLD_GREEN
    long_normal_linear_fallback: StandardParticle.NOTE_LINEAR_HOLD_GREEN
    long_accent_circular_fallback: StandardParticle.NOTE_CIRCULAR_HOLD_YELLOW
    long_accent_linear_fallback: StandardParticle.NOTE_LINEAR_HOLD_YELLOW
    damage_note_circular_fallback: StandardParticle.NOTE_CIRCULAR_TAP_PURPLE
    damage_note_linear_fallback: StandardParticle.NOTE_LINEAR_TAP_PURPLE


EMPTY_PARTICLE = Particle(-1)


class NoteParticleSet(Record):
    circular: Particle
    linear: Particle
    directional: Particle
    tick: Particle
    lane: Particle
    lane_basic: Particle
    slot_linear: Particle


EMPTY_NOTE_PARTICLE_SET = NoteParticleSet(
    circular=EMPTY_PARTICLE,
    linear=EMPTY_PARTICLE,
    directional=EMPTY_PARTICLE,
    tick=EMPTY_PARTICLE,
    lane=EMPTY_PARTICLE,
    lane_basic=EMPTY_PARTICLE,
    slot_linear=EMPTY_PARTICLE,
)


class ActiveConnectorParticleSet(Record):
    circular: Particle
    linear: Particle
    trail_linear: Particle
    slot_linear: Particle


def first_available_particle(*args: Particle) -> Particle:
    result = +EMPTY_PARTICLE
    for e in args:
        if e.is_available:
            result @= e
            break
    return result


@level_data
class ActiveParticles:
    lane: Particle

    normal_note: NoteParticleSet
    slide_note: NoteParticleSet
    flick_note: NoteParticleSet
    critical_note: NoteParticleSet
    critical_slide_note: NoteParticleSet
    critical_flick_note: NoteParticleSet
    trace_note: NoteParticleSet
    trace_flick_note: NoteParticleSet
    critical_trace_note: NoteParticleSet
    critical_trace_flick_note: NoteParticleSet
    normal_slide_tick_note: NoteParticleSet
    critical_slide_tick_note: NoteParticleSet
    damage_note: NoteParticleSet

    normal_slide_connector: ActiveConnectorParticleSet
    critical_slide_connector: ActiveConnectorParticleSet


def init_particles():
    ActiveParticles.lane @= BaseParticles.lane

    ActiveParticles.normal_note @= NoteParticleSet(
        circular=first_available_particle(
            BaseParticles.normal_note_circular,
            BaseParticles.normal_note_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.normal_note_linear,
            BaseParticles.normal_note_linear_fallback,
        ),
        directional=EMPTY_PARTICLE,
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(BaseParticles.normal_note_lane_linear),
        lane_basic=BaseParticles.lane,
        slot_linear=first_available_particle(BaseParticles.slot_normal_linear),
    )
    ActiveParticles.slide_note @= NoteParticleSet(
        circular=first_available_particle(
            BaseParticles.long_note_circular,
            BaseParticles.long_note_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.long_note_linear,
            BaseParticles.long_note_linear_fallback,
        ),
        directional=EMPTY_PARTICLE,
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(
            BaseParticles.normal_slide_note_lane_linear,
            BaseParticles.normal_note_lane_linear,
        ),
        lane_basic=BaseParticles.lane,
        slot_linear=first_available_particle(BaseParticles.slot_long_linear),
    )
    ActiveParticles.flick_note @= NoteParticleSet(
        circular=first_available_particle(
            BaseParticles.flick_note_circular,
            BaseParticles.flick_note_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.flick_note_linear,
            BaseParticles.flick_note_linear_fallback,
        ),
        directional=first_available_particle(
            BaseParticles.flick_note_directional,
            BaseParticles.flick_note_directional_fallback,
        ),
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(BaseParticles.normal_flick_note_lane_linear),
        lane_basic=EMPTY_PARTICLE,
        slot_linear=first_available_particle(BaseParticles.slot_flick_linear),
    )
    ActiveParticles.critical_note @= NoteParticleSet(
        circular=first_available_particle(
            BaseParticles.accent_note_circular,
            BaseParticles.accent_note_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.accent_note_linear,
            BaseParticles.accent_note_linear_fallback,
        ),
        directional=EMPTY_PARTICLE,
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(BaseParticles.critical_note_lane_linear),
        lane_basic=BaseParticles.lane,
        slot_linear=first_available_particle(BaseParticles.slot_accent_linear),
    )
    ActiveParticles.critical_slide_note @= NoteParticleSet(
        circular=first_available_particle(
            BaseParticles.accent_note_circular,
            BaseParticles.accent_note_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.accent_note_linear,
            BaseParticles.accent_note_linear_fallback,
        ),
        directional=EMPTY_PARTICLE,
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(
            BaseParticles.critical_slide_note_lane_linear,
            BaseParticles.critical_note_lane_linear,
        ),
        lane_basic=BaseParticles.lane,
        slot_linear=first_available_particle(BaseParticles.slot_accent_linear),
    )
    ActiveParticles.critical_flick_note @= NoteParticleSet(
        circular=first_available_particle(
            BaseParticles.accent_note_circular,
            BaseParticles.accent_note_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.accent_note_linear,
            BaseParticles.accent_note_linear_fallback,
        ),
        directional=first_available_particle(
            BaseParticles.accent_note_directional,
            BaseParticles.accent_note_directional_fallback,
        ),
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(BaseParticles.critical_flick_note_lane_linear),
        lane_basic=BaseParticles.lane,
        slot_linear=first_available_particle(BaseParticles.slot_accent_linear),
    )
    ActiveParticles.trace_note @= NoteParticleSet(
        circular=EMPTY_PARTICLE,
        linear=first_available_particle(
            BaseParticles.long_note_linear,
            BaseParticles.long_note_linear_fallback,
        ),
        directional=EMPTY_PARTICLE,
        tick=first_available_particle(
            BaseParticles.long_note_circular,
            BaseParticles.long_note_circular_fallback,
        ),
        lane=EMPTY_PARTICLE,
        lane_basic=EMPTY_PARTICLE,
        slot_linear=EMPTY_PARTICLE,
    )
    ActiveParticles.trace_flick_note @= NoteParticleSet(
        circular=EMPTY_PARTICLE,
        linear=EMPTY_PARTICLE,
        directional=first_available_particle(
            BaseParticles.flick_note_directional,
            BaseParticles.flick_note_directional_fallback,
        ),
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(BaseParticles.normal_flick_note_lane_linear),
        lane_basic=EMPTY_PARTICLE,
        slot_linear=EMPTY_PARTICLE,
    )
    ActiveParticles.critical_trace_note @= NoteParticleSet(
        circular=EMPTY_PARTICLE,
        linear=first_available_particle(
            BaseParticles.accent_note_linear,
            BaseParticles.accent_note_linear_fallback,
        ),
        directional=EMPTY_PARTICLE,
        tick=first_available_particle(
            BaseParticles.accent_note_circular,
            BaseParticles.accent_note_circular_fallback,
        ),
        lane=EMPTY_PARTICLE,
        lane_basic=EMPTY_PARTICLE,
        slot_linear=EMPTY_PARTICLE,
    )
    ActiveParticles.critical_trace_flick_note @= NoteParticleSet(
        circular=EMPTY_PARTICLE,
        linear=EMPTY_PARTICLE,
        directional=first_available_particle(
            BaseParticles.accent_note_directional,
            BaseParticles.accent_note_directional_fallback,
        ),
        tick=EMPTY_PARTICLE,
        lane=first_available_particle(BaseParticles.critical_flick_note_lane_linear),
        lane_basic=EMPTY_PARTICLE,
        slot_linear=EMPTY_PARTICLE,
    )
    ActiveParticles.normal_slide_tick_note @= NoteParticleSet(
        circular=EMPTY_PARTICLE,
        linear=EMPTY_PARTICLE,
        directional=EMPTY_PARTICLE,
        tick=first_available_particle(
            BaseParticles.normal_relay,
            BaseParticles.normal_relay_fallback,
        ),
        lane=EMPTY_PARTICLE,
        lane_basic=EMPTY_PARTICLE,
        slot_linear=EMPTY_PARTICLE,
    )
    ActiveParticles.critical_slide_tick_note @= NoteParticleSet(
        circular=EMPTY_PARTICLE,
        linear=EMPTY_PARTICLE,
        directional=EMPTY_PARTICLE,
        tick=first_available_particle(
            BaseParticles.accent_relay,
            BaseParticles.accent_relay_fallback,
        ),
        lane=EMPTY_PARTICLE,
        lane_basic=EMPTY_PARTICLE,
        slot_linear=EMPTY_PARTICLE,
    )
    ActiveParticles.damage_note @= NoteParticleSet(
        circular=first_available_particle(
            BaseParticles.damage_note_circular,
            BaseParticles.damage_note_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.damage_note_linear,
            BaseParticles.damage_note_linear_fallback,
        ),
        directional=EMPTY_PARTICLE,
        tick=EMPTY_PARTICLE,
        lane=EMPTY_PARTICLE,
        lane_basic=EMPTY_PARTICLE,
        slot_linear=EMPTY_PARTICLE,
    )

    ActiveParticles.normal_slide_connector @= ActiveConnectorParticleSet(
        circular=first_available_particle(
            BaseParticles.long_normal_circular,
            BaseParticles.long_normal_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.long_normal_linear,
            BaseParticles.long_normal_linear_fallback,
        ),
        trail_linear=first_available_particle(BaseParticles.long_normal_trail_linear),
        slot_linear=first_available_particle(BaseParticles.long_normal_slot_linear),
    )
    ActiveParticles.critical_slide_connector @= ActiveConnectorParticleSet(
        circular=first_available_particle(
            BaseParticles.long_accent_circular,
            BaseParticles.long_accent_circular_fallback,
        ),
        linear=first_available_particle(
            BaseParticles.long_accent_linear,
            BaseParticles.long_accent_linear_fallback,
        ),
        trail_linear=first_available_particle(BaseParticles.long_accent_trail_linear),
        slot_linear=first_available_particle(BaseParticles.long_accent_slot_linear),
    )
