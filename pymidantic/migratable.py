from __future__ import annotations

from collections import defaultdict, deque
from typing import (
    Any,
    ClassVar,
    Literal,
    Mapping,
    Protocol,
    TypedDict,
    Unpack,
)

from pydantic import BaseModel
from pydantic.main import IncEx

_migration_store: dict[type[Migratable], dict[tuple[str, str], Any]] = defaultdict(dict)


def _find_route(edges: list[tuple[str, str]], start: str, end: str) -> list[str] | None:
    next_nodes: dict[str, list[str]] = defaultdict(list)
    for s, e in edges:
        next_nodes[s].append(e)

    queue = deque([start])
    prev_node_in_path: dict[str, str] = {}
    while queue:
        node = queue.popleft()

        if node == end:
            break

        for next in next_nodes[node]:
            if next not in prev_node_in_path:
                prev_node_in_path[next] = node
                queue.append(next)

    if end not in prev_node_in_path:
        return None

    path = [end]
    while path[0] != start:
        path.insert(0, prev_node_in_path[path[0]])

    return path


class Migratable(BaseModel):
    _version: ClassVar[str] = NotImplemented

    class ModelDumpKwargs(TypedDict, total=False):
        mode: Literal["json", "python"] | str
        include: IncEx
        exclude: IncEx
        context: Any | None
        by_alias: bool
        exclude_unset: bool
        exclude_defaults: bool
        exclude_none: bool
        round_trip: bool
        warnings: bool | Literal["none", "warn", "error"]
        serialize_as_any: bool

    def dump_version(
        self,
        version: str,
        additional_data: Mapping[str, Any] | None = None,
        **kwargs: Unpack[ModelDumpKwargs],
    ) -> dict[str, Any]:
        """tries to output this model at the specified version.

        Raises if there is no path (defined with `@migrate` decorators) from the current version to the requested one.

        If the path to the version you require needs more data than is in the model currently it can be provided in the
        additional_data dict which is passed to the migration functions.

        kwargs will be passed to `BaseModel.model_dump`
        """

        if additional_data is None:
            additional_data = {}

        attrs = self.model_dump(**kwargs)

        if version == self._version:
            return attrs

        path = _find_route(list(_migration_store[self.__class__]), self._version, version)
        if not path:
            raise ValueError(f"Found no path found for {type(self).__name__} from {self._version} to {version}")

        previous = self._version
        for node in path[1:]:
            _migration_store[self.__class__][(previous, node)](attrs, additional_data)
            previous = node
        return attrs


class Migrator(Protocol):
    def __call__(self, attrs: dict[str, Any], additional_data: dict[str, Any]) -> None: ...


def migrate(migrating_class: type[Migratable], from_version: str, to_version: str):
    def decorator(f: Migrator):
        def wrapped(attrs: dict[str, Any], additional_data: dict[str, Any]):
            f(attrs, additional_data)

        _migration_store[migrating_class][(from_version, to_version)] = wrapped

        return wrapped

    return decorator
