from ape import plugins


@plugins.register(plugins.AccountPlugin)
def account_types():
    from .accounts import Account, AccountContainer

    return AccountContainer, Account


__all__ = [
    "AccountContainer",
    "Account",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module 'ape_turnkey' has not attribute '{name}'")

    from importlib import import_module

    return getattr(import_module("ape_turnkey.accounts"), name)
