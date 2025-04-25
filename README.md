# Overview

Ape account plugin and CLI for [Turnkey](https://turnkey.com).
Recommended plugin for automation and use with the [Silverback Platform](https://silverback.apeworx.io).

## Dependencies

- [python3](https://www.python.org/downloads) version 3.9 up to 3.13.

## Installation

### via `pip`

You can install the latest release via [`pip`](https://pypi.org/project/pip/):

```bash
pip install ape-turnkey
```

### via `setuptools`

You can clone the repository and use [`setuptools`](https://github.com/pypa/setuptools) for the most up-to-date version:

```bash
git clone https://github.com/ApeWorX/ape-turnkey.git
cd ape-turnkey
python3 setup.py install
```

## Usage

In order to use this plugin, you will need the `TURNKEY_ORGANIZATION_ID`, `TURNKEY_API_PUBLIC_KEY`, and `TURNKEY_API_PRIVATE_KEY` variables.
You can see which account you are signed in with using the following command:

```sh
$ ape turnkey whoami
Logged in as '<your account nickname>' under '<organization name>'
```

After that, you can do actions like list your wallets:

```sh
$ ape turnkey wallets list
...
```

You can create a new wallet via:

```sh
$ ape turnkey wallets new turnkey-wallet ...
SUCCESS: Wallet ID '1234....beef' created!
```

You will then be able to use this wallet for signing messages and transactions with Ape now, for example:

```py
$ ape console

 In[0]: acct = accounts.load("turnkey-wallet/0")

 In[1]: acct.sign_message("Signing using the turnkey API!")
Out[1]: <MessageSignature v=0 r=... s=...>
```

```{notice}
Turnkey account aliases follow the convention of `<wallet name>/<account index>` since a wallet can have more than one associated account
```

## Development

Please see the [contributing guide](CONTRIBUTING.md) to learn more how to contribute to this project.
Comments, questions, criticisms and pull requests are welcomed.
