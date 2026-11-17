"""Public-candidate packaging change: SDK-only; never absorb local built UI/state.

Modified for this source candidate; original copyright/NOTICE remains applicable.
"""

import os

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name != "wheel":
            return
        if os.environ.get("ZYNTRAVA_BUILD_PROFILE", "research") != "research":
            raise ValueError(
                "This source candidate supports SDK-only packages, not desktop binaries"
            )
        for number in (1, 2, 3):
            build_data["force_include"][f"benchmarks/corpus-v{number}.json"] = (
                f"zyntrava/data/corpus-v{number}.json"
            )
        for name in ("local-model.json", "qwen3-0.6b.json", "qwen3-4b.json"):
            build_data["force_include"][f"models/{name}"] = f"zyntrava/data/{name}"
