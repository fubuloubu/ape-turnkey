from functools import wraps

import click
from eth_account.hdaccount import ETHEREUM_DEFAULT_PATH

from ape_turnkey.client import AccountSpec, TurnkeyClient


@wraps(click.option)
def uses_client(**other_kwargs):
    from ape_turnkey.client import TurnkeyClient

    return click.option(
        "--api-url",
        "client",
        default=TurnkeyClient.ENDPOINT,
        callback=lambda ctx, param, val: TurnkeyClient(),
        **other_kwargs,
    )


def success(msg: str) -> str:
    return f"{click.style('SUCCESS: ', fg='green')} {msg}"


@click.group(short_help="Interact with Turnkey (https://turnkey.com)")
def cli():
    """
    Commands for working with Turnkey service, including managing login, users, wallets, and more.
    """


@cli.command()
@uses_client()
def whoami(client: TurnkeyClient):
    """Get account information for logged in account."""
    whoami = client.whoami()
    click.echo(f"Logged in as '{whoami.username}' under '{whoami.organizationName}'")


@cli.group()
def users():
    """Commands for managing users via the Turnkey API."""


@users.command(name="list")
@uses_client()
def list_users(client: TurnkeyClient):
    for user in client.get_users():
        click.echo(user.name)


@cli.group()
def wallets():
    """Commands for managing wallets via the Turnkey API."""


@wallets.command(name="new")
@uses_client()
@click.option("-n", "--num-accounts", type=int, default=1)
@click.option("--mnemonic-length", default="12", type=click.Choice(("12", "15", "18", "21", "24")))
@click.argument("name")
def new_wallet(client: TurnkeyClient, name: str, num_accounts: int, mnemonic_length: str):
    wallet_id = client.create_wallet(
        name,
        *(AccountSpec(path=f"{ETHEREUM_DEFAULT_PATH[:-1]}{idx}") for idx in range(num_accounts)),
        mnemonic_length=int(mnemonic_length),
    )
    click.echo(success(f"Wallet ID '{wallet_id}' created!"))


@wallets.command(name="list")
@uses_client()
def list_wallets(client: TurnkeyClient):
    for wallet in client.get_wallets():
        click.echo(wallet.name)


@wallets.command()
@uses_client()
@click.argument("wallet_name")
def accounts(client: TurnkeyClient, wallet_name: str):
    for wallet in client.get_wallets():
        if wallet.name == wallet_name:
            break

    else:
        raise click.UsageError(f"Wallet '{wallet_name}' is unknown.")

    for account in client.get_wallet_accounts(wallet.id):
        click.echo(account.address)
