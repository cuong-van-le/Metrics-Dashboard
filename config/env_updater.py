import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvUpdater:
    def __init__(self, env_path: Path = Path(".env")):
        self.env_path = env_path

    def update(
        self,
        role_arn: str | None = None,
        bucket_arn: str | None = None,
        lambda_arn: str | None = None,
    ) -> bool:
        if not self.env_path.exists():
            logger.warning(f"{self.env_path} does not exist. Skipping .env update.")
            return False

        lines = self.env_path.read_text(encoding="utf-8").splitlines()
        updated = False

        updates = {
            "ROLE_ARN": role_arn,
            "BUCKET_ARN": bucket_arn,
            "LAMBDA_ARN": lambda_arn,
        }

        new_lines = []
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0].strip()
                if key in updates and updates[key]:
                    current_value = line.split("=", 1)[1].strip() if "=" in line else ""
                    if not current_value or current_value != updates[key]:
                        new_lines.append(f"{key}={updates[key]}")
                        updated = True
                        logger.info(f"Updated {key} in .env")
                        continue
            new_lines.append(line)

        existing_keys = {
            line.split("=")[0].strip()
            for line in lines
            if "=" in line and not line.strip().startswith("#")
        }
        for key, value in updates.items():
            if key not in existing_keys and value:
                new_lines.append(f"{key}={value}")
                updated = True
                logger.info(f"Added {key} to .env")

        if updated:
            self.env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            logger.info(f"Updated {self.env_path}")
        else:
            logger.debug("No changes needed in .env")

        return updated
