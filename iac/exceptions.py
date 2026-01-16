class ResourceCreationError(Exception):
    pass


class LambdaCreationError(ResourceCreationError):
    pass


class IAMPropagationError(ResourceCreationError):
    pass


class BucketCreationError(ResourceCreationError):
    pass


class FirehoseCreationError(ResourceCreationError):
    pass


class RoleCreationError(ResourceCreationError):
    pass
