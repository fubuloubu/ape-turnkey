from functools import cached_property
from typing import TYPE_CHECKING, Any, Iterator

import rlp  # type: ignore[import-untyped]
from ape.api import AccountAPI, AccountContainerAPI, TransactionAPI
from ape.types.signatures import MessageSignature, SignableMessage, TransactionSignature
from eip712.messages import EIP712Message
from eth_account._utils.legacy_transactions import serializable_unsigned_transaction_from_dict
from eth_account._utils.transaction_utils import transaction_rpc_to_rlp_structure
from eth_account.messages import encode_defunct
from eth_utils import to_bytes, to_hex

from .client import TurnkeyClient, Wallet, WalletAccount

if TYPE_CHECKING:
    from ape.types import AddressType


class AccountContainer(AccountContainerAPI):
    @cached_property
    def client(self) -> TurnkeyClient:
        return TurnkeyClient()

    def __len__(self) -> int:
        return len(list(self.accounts))

    @property
    def aliases(self) -> Iterator[str]:
        yield from map(lambda a: a.alias, self.accounts)

    @property
    def accounts(self) -> Iterator["Account"]:
        for wallet in self.client.get_wallets():
            for account in self.client.get_wallet_accounts(wallet.id):
                yield Account(wallet=wallet, wallet_account=account)


class Account(AccountAPI):
    wallet: Wallet
    wallet_account: WalletAccount

    @cached_property
    def client(self) -> TurnkeyClient:
        return TurnkeyClient()

    @property
    def alias(self) -> str:
        last_index = self.wallet_account.path.split("/")[-1]
        return f"{self.wallet.name}/{last_index}"

    @property
    def address(self) -> "AddressType":
        return self.wallet_account.address

    def sign_message(self, msg: Any, **signer_options):
        if isinstance(msg, str):
            msg = encode_defunct(text=msg)

        elif isinstance(msg, int):
            msg = encode_defunct(hexstr=to_hex(msg))

        elif isinstance(msg, bytes):
            msg = encode_defunct(primitive=msg)

        elif isinstance(msg, EIP712Message):
            # Convert EIP712Message to SignableMessage for handling below
            msg = msg.signable_message

        if not isinstance(msg, SignableMessage):
            msg = msg

        sig = self.wallet_account.sign_raw_payload(
            (b"\x19" + msg.version + msg.header + msg.body).hex()
        )

        return MessageSignature(
            v=int(sig["v"]),
            r=bytes.fromhex(sig["r"]),
            s=bytes.fromhex(sig["s"]),
        )

    def sign_transaction(self, txn: TransactionAPI, **signer_options):
        # NOTE: `from` is ignored for serialized txns, `type` depends on legacy or not
        txn_dict = txn.model_dump(exclude={"sender", "type"})
        unsigned_txn = serializable_unsigned_transaction_from_dict(txn_dict)

        # Serialize into raw bytes for signer API
        # TODO: Make this easier in Ape? e.g. `txn.encode()` works either signed or unsigned
        if txn.type:
            txn_class = unsigned_txn.transaction.__class__
            rlp_serializer = txn_class._unsigned_transaction_serializer  # type: ignore[union-attr]
            rlp_structured_dict = transaction_rpc_to_rlp_structure(txn_dict)
            # TODO: Why is this necessary? Really annoying to have to do this
            rlp_structured_dict["to"] = to_bytes(hexstr=rlp_structured_dict["to"])
            rlp_structured_dict["data"] = to_bytes(hexstr=rlp_structured_dict["data"])
            rlp_struct = rlp_serializer.from_dict(rlp_structured_dict)

        else:  # NOTE: Legacy Transaction type can just encode directly
            rlp_struct = unsigned_txn

        encoded_unsigned_txn = rlp.encode(rlp_struct)

        if txn.type:  # NOTE: Typed transactions must start with their 1 byte type code
            encoded_unsigned_txn = bytes([txn.type]) + encoded_unsigned_txn

        sig = self.wallet_account.sign_raw_payload(encoded_unsigned_txn.hex())
        txn.signature = TransactionSignature(
            v=int(sig["v"]),
            r=bytes.fromhex(sig["r"]),
            s=bytes.fromhex(sig["s"]),
        )

        return txn
