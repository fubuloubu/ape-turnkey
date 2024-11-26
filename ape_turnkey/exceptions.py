from ape.exceptions import ApeException


class TurnkeyPluginError(ApeException):
    pass


class ClientError(TurnkeyPluginError):
    pass
