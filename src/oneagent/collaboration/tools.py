"""Domain-neutral tool registration. Apps own validation and action authorization."""
from dataclasses import dataclass
from typing import Callable

from .store import identifier, object_value


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable
    validate: Callable
    mutating: bool = False


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool: Tool):
        identifier(tool.name)
        if tool.name in self._tools:
            raise ValueError("Duplicate tool name")
        self._tools[tool.name] = tool

    def descriptions(self):
        return [{"name": t.name, "description": t.description, "input_schema": t.input_schema,
                 "mutating": t.mutating} for t in self._tools.values()]

    def invoke(self, name, arguments, *, owner, request_id, authorize=lambda *_: False):
        tool = self._tools[name]
        arguments = object_value(arguments)
        tool.validate(arguments)
        if tool.mutating and not authorize(owner, name, arguments):
            raise PermissionError("Action was not authorized")
        # For state-changing effects, the app handler must durably deduplicate this ID.
        return tool.handler(owner, arguments, identifier(request_id))
