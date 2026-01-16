class RetryConfig:
    MAX_RETRIES = 3
    BASE_WAIT_SECONDS = 5
    MAX_WAIT_SECONDS = 15


class AWSConstants:
    US_EAST_1 = "us-east-1"
    DEFAULT_LAMBDA_RUNTIME = "python3.12"
    DEFAULT_LAMBDA_HANDLER = "app.handler"
    DEFAULT_LAMBDA_TIMEOUT = 60
    DEFAULT_LAMBDA_MEMORY_MB = 256


class ErrorCodes:
    RESOURCE_NOT_FOUND = "ResourceNotFoundException"
    BUCKET_ALREADY_EXISTS = "BucketAlreadyExists"
    BUCKET_ALREADY_OWNED = "BucketAlreadyOwnedByYou"
    INVALID_PARAMETER = "InvalidParameterValueException"
    INVALID_ARGUMENT = "InvalidArgumentException"
    NO_SUCH_ENTITY = "NoSuchEntity"
    ENTITY_ALREADY_EXISTS = "EntityAlreadyExists"
    RESOURCE_IN_USE = "ResourceInUseException"
