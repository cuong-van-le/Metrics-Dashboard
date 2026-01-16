from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, Dict, List

from iac.base import Resource, ResourceResult
from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ResourceDependency:
    resource_name: str
    depends_on: List[str]
    factory: Callable[[Dict[str, ResourceResult]], Resource[ResourceResult]]


class InfrastructureOrchestrator:
    def __init__(self):
        self.resources: Dict[str, Resource[ResourceResult]] = {}
        self.dependencies: List[ResourceDependency] = []
        self.factories: Dict[str, Callable[[Dict[str, ResourceResult]], Resource[ResourceResult]]] = {}

    def register(
        self, 
        name: str, 
        resource: Resource[ResourceResult] | None = None,
        depends_on: List[str] | None = None,
        factory: Callable[[Dict[str, ResourceResult]], Resource[ResourceResult]] | None = None
    ):
        if resource:
            self.resources[name] = resource
        if factory:
            self.factories[name] = factory
        if depends_on and factory:
            self.dependencies.append(ResourceDependency(name, depends_on, factory))

    def ensure_all(self) -> Dict[str, ResourceResult]:
        order = self._topological_sort()
        results = {}

        for resource_name in order:
            if resource_name in self.factories:
                resource = self.factories[resource_name](results)
            else:
                resource = self.resources[resource_name]
            results[resource_name] = resource.ensure()

        return results

    def _topological_sort(self) -> List[str]:
        all_resources = set(self.resources.keys()) | set(self.factories.keys())
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for resource_name in all_resources:
            in_degree[resource_name] = 0

        for dep in self.dependencies:
            for dep_name in dep.depends_on:
                graph[dep_name].append(dep.resource_name)
                in_degree[dep.resource_name] += 1

        queue = deque([name for name in all_resources if in_degree[name] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(all_resources):
            raise RuntimeError("Circular dependency detected in resource graph")

        return result
