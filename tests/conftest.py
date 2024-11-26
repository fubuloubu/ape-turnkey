import pytest
from ape import accounts

# NOTE: Need to do this because `accounts` fixture is only test accounts


@pytest.fixture(scope="session")
def turnkey_container():
    return accounts.containers["turnkey"]
