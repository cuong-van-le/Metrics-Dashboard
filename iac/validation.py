import re


class ResourceValidator:
    @staticmethod
    def validate_bucket_name(name: str) -> bool:
        if not isinstance(name, str):
            return False

        if not (3 <= len(name) <= 63):
            return False

        if not re.match(r"^[a-z0-9.-]+$", name):
            return False

        if name.startswith(".") or name.endswith("."):
            return False
        if name.startswith("-") or name.endswith("-"):
            return False

        if ".." in name:
            return False

        if re.match(r"^\d+\.\d+\.\d+\.\d+$", name):
            return False

        return True

    @staticmethod
    def validate_lambda_name(name: str) -> bool:
        if not isinstance(name, str):
            return False

        if not (1 <= len(name) <= 64):
            return False

        if not re.match(r"^[a-zA-Z0-9-_]+$", name):
            return False

        return True

    @staticmethod
    def validate_role_name(name: str) -> bool:
        if not isinstance(name, str):
            return False

        if not (1 <= len(name) <= 64):
            return False

        if not re.match(r"^[a-zA-Z0-9+=,.@_-]+$", name):
            return False

        return True

    @staticmethod
    def validate_firehose_stream_name(name: str) -> bool:
        if not isinstance(name, str):
            return False

        if not (1 <= len(name) <= 64):
            return False

        if not re.match(r"^[a-zA-Z0-9-_]+$", name):
            return False

        return True

    @staticmethod
    def validate_arn(arn: str) -> bool:
        if not isinstance(arn, str):
            return False

        parts = arn.split(":")
        if len(parts) < 4 or parts[0] != "arn" or parts[1] != "aws":
            return False

        if len(parts) < 4:
            return False

        if not re.match(r"^[a-z0-9-]+$", parts[2]):
            return False

        resource_parts = [p for p in parts[3:] if p]
        if not resource_parts:
            return False

        resource_part = ":".join(resource_parts)
        if not resource_part.strip():
            return False

        return True

    @staticmethod
    def validate_s3_arn(arn: str) -> bool:
        if not isinstance(arn, str):
            return False

        pattern = r"^arn:aws:s3:::[\w.-]+$"
        return bool(re.match(pattern, arn))

    @staticmethod
    def validate_lambda_arn(arn: str) -> bool:
        if not isinstance(arn, str):
            return False

        pattern = r"^arn:aws:lambda:[a-z0-9-]+:[0-9]{12}:function:[a-zA-Z0-9-_]+$"
        return bool(re.match(pattern, arn))

    @staticmethod
    def validate_iam_role_arn(arn: str) -> bool:
        if not isinstance(arn, str):
            return False

        pattern = r"^arn:aws:iam::[0-9]{12}:role/[a-zA-Z0-9+=,.@_-]+$"
        return bool(re.match(pattern, arn))
