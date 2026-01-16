import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class ResourceResult:
    pass


class Resource(ABC, Generic[T]):
    def __init__(self, config: dict[str, Any], client: Any):
        self.config = config
        self.client = client

    def ensure(self) -> T:
        resource_name = self._get_resource_name()
        resource_type = self.__class__.__name__
        start_time = time.time()
        success = True
        error_msg = ""
        operation = "unknown"
        result = None

        try:
            if self._exists(resource_name):
                logger.info(f"{resource_type} exists: {resource_name}")
                result = self._handle_existing(resource_name)
                operation = "handle_existing"
            else:
                logger.info(f"{resource_type} not found. Creating: {resource_name}")
                result = self._create(resource_name)
                operation = "create"
        except Exception as e:
            success = False
            error_msg = str(e)
            operation = "error"
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            try:
                from metrics.agent import get_collector

                collector = get_collector()
                collector.record_operation(
                    resource_type=resource_type,
                    resource_name=resource_name,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                )
            except Exception:  # nosec B110
                pass

        return result

    @abstractmethod
    def _get_resource_name(self) -> str:
        pass

    @abstractmethod
    def _exists(self, name: str) -> bool:
        pass

    @abstractmethod
    def _handle_existing(self, name: str) -> T:
        pass

    @abstractmethod
    def _create(self, name: str) -> T:
        pass
