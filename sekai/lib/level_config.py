from enum import IntEnum

from sonolus.script.globals import level_data


class EngineRevision(IntEnum):
    BASE = 0
    SONOLUS_1_1_0 = 1

    LATEST = 1


@level_data
class LevelConfig:
    revision: EngineRevision


def init_level_config(
    revision: EngineRevision = EngineRevision.LATEST,
):
    LevelConfig.revision = revision
