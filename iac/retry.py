import logging
import time
from functools import wraps
from typing import Callable, TypeVar, Tuple

from botocore.exceptions import ClientError

from iac.constants import RetryConfig, ErrorCodes

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_on_iam_propagation(
    max_retries: int = RetryConfig.MAX_RETRIES,
    base_wait: int = RetryConfig.BASE_WAIT_SECONDS,
    error_codes: Tuple[str, ...] = (
        ErrorCodes.INVALID_PARAMETER,
        ErrorCodes.INVALID_ARGUMENT,
    ),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    error_msg = str(e).lower()

                    if error_code in error_codes and (
                        "cannot be assumed" in error_msg
                        or "unable to assume role" in error_msg
                    ):
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * base_wait
                            logger.warning(
                                f"Role not ready, waiting {wait_time}s before retry "
                                f"{attempt + 1}/{max_retries}..."
                            )
                            time.sleep(wait_time)
                            continue
                    raise
            raise RuntimeError(f"Failed after {max_retries} retries")

        return wrapper

    return decorator
