import pytest


def test_account_container(turnkey_container):
    assert len(turnkey_container) > 0, "Needed for testing"


def test_account_class(turnkey_container):
    account = next(turnkey_container.accounts)
    assert account.address


def test_message_signing(turnkey_container):
    account = next(turnkey_container.accounts)
    message = "Signed with Turnkey API"
    assert account.check_signature(message, account.sign_message(message))


@pytest.mark.parametrize("use_legacy", [False, True])
def test_transaction_signing(accounts, turnkey_container, use_legacy):
    account = next(turnkey_container.accounts)
    # NOTE: Need this so account has some gas for testing
    accounts[0].transfer(account, "1 ether")

    txn_kwargs = dict()
    if use_legacy:
        txn_kwargs["gas_price"] = "1 gwei"

    account.transfer(account, "0.1 ether", **txn_kwargs)
