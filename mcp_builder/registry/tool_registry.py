
import json
from pathlib import Path
from typing import Any


# ============================================================
# Persistent storage
# ============================================================

REGISTRY_FILE = (
    Path(__file__).resolve().parent / "tools.json"
)


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

        self._load()

    # ========================================================
    # Load tools from disk
    # ========================================================

    def _load(self):

        if not REGISTRY_FILE.exists():

            self._tools = {}

            return

        try:

            with open(
                REGISTRY_FILE,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            if isinstance(data, dict):

                self._tools = data

            else:

                self._tools = {}

        except (
            json.JSONDecodeError,
            OSError,
        ):

            self._tools = {}

    # ========================================================
    # Save tools to disk
    # ========================================================

    def _save(self):

        REGISTRY_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            REGISTRY_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                self._tools,
                file,
                indent=2,
            )

    # ========================================================
    # Register
    # ========================================================

    def register(
        self,
        tool_definition: dict[str, Any],
    ) -> dict[str, Any]:

        name = tool_definition.get("name")

        if not name:

            raise ValueError(
                "Tool name is required"
            )

        self._tools[name] = tool_definition

        self._save()

        return tool_definition

    # ========================================================
    # Get
    # ========================================================

    def get(
        self,
        name: str,
    ) -> dict[str, Any] | None:

        return self._tools.get(name)

    # ========================================================
    # List
    # ========================================================

    def list(self) -> list[dict[str, Any]]:

        return list(
            self._tools.values()
        )

    # ========================================================
    # Remove
    # ========================================================

    def remove(
        self,
        name: str,
    ) -> bool:

        if name not in self._tools:

            return False

        del self._tools[name]

        self._save()

        return True


# ============================================================
# Global registry
# ============================================================

tool_registry = ToolRegistry()

