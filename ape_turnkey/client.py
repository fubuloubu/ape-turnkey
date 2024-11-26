import json
import os
import uuid
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from enum import Enum
from functools import cached_property
from typing import ClassVar

import requests
from ape.types import AddressType  # noqa: TC002
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from eth_account.hdaccount import ETHEREUM_DEFAULT_PATH
from pydantic import BaseModel, Field, field_validator

from .exceptions import ClientError


class ActivityType(str, Enum):
    CREATE_WALLET = "ACTIVITY_TYPE_CREATE_WALLET"
    SIGN_RAW_PAYLOAD_V2 = "ACTIVITY_TYPE_SIGN_RAW_PAYLOAD_V2"

    def __str__(self) -> str:
        return self.value


class User(BaseModel):
    id: uuid.UUID = Field(alias="userId")
    name: str = Field(alias="userName")

    email: str | None = Field(default=None, alias="userEmail")
    phone: str | None = Field(default=None, alias="userPhoneNumber")

    # authenticators: list[Authenticator]
    # api_keys: list[ApiKey]
    # tags: list[TagID]
    # oauth_providers: list[OAuthProvider]

    created: datetime = Field(alias="createdAt")
    updated: datetime = Field(alias="updatedAt")

    @field_validator("created", "updated", mode="before")
    def convert_to_datetime(cls, data: dict) -> datetime:
        return datetime.fromtimestamp(float(f"{data['seconds']}.{data['nanos']}"), tz=timezone.utc)


class CurveType(str, Enum):
    SECP256K1 = "CURVE_SECP256K1"

    def __str__(self) -> str:
        return self.value


class PathFormat(str, Enum):
    BIP32 = "PATH_FORMAT_BIP32"

    def __str__(self) -> str:
        return self.value


class AddressFormat(str, Enum):
    ETHEREUM = "ADDRESS_FORMAT_ETHEREUM"

    def __str__(self) -> str:
        return self.value


class AccountSpec(BaseModel):
    curve: CurveType = CurveType.SECP256K1
    path_format: PathFormat = Field(default=PathFormat.BIP32, alias="pathFormat")
    path: str = ETHEREUM_DEFAULT_PATH
    address_format: AddressFormat = Field(default=AddressFormat.ETHEREUM, alias="addressFormat")


class Wallet(BaseModel):
    id: uuid.UUID = Field(alias="walletId")
    name: str = Field(alias="walletName")
    imported: bool
    exported: bool

    created: datetime = Field(alias="createdAt")
    updated: datetime = Field(alias="updatedAt")

    @field_validator("created", "updated", mode="before")
    def convert_to_datetime(cls, data: dict) -> datetime:
        return datetime.fromtimestamp(float(f"{data['seconds']}.{data['nanos']}"), tz=timezone.utc)


class TransactionType(str, Enum):
    ETHEREUM = "TRANSACTION_TYPE_ETHEREUM"

    def __str__(self) -> str:
        return self.value


class WalletAccount(BaseModel):
    _client: ClassVar["TurnkeyClient"]  # inject before use

    id: uuid.UUID = Field(alias="walletAccountId")
    organization_id: uuid.UUID = Field(alias="organizationId")
    wallet_id: uuid.UUID = Field(alias="walletId")
    path: str
    address: AddressType

    created: datetime = Field(alias="createdAt")
    updated: datetime = Field(alias="updatedAt")

    @field_validator("created", "updated", mode="before")
    def convert_to_datetime(cls, data: dict) -> datetime:
        return datetime.fromtimestamp(float(f"{data['seconds']}.{data['nanos']}"), tz=timezone.utc)

    def sign_raw_payload(self, payload: str) -> dict:
        return self._client.sign_raw_payload(
            signWith=self.address,
            payload=payload,
            encoding="PAYLOAD_ENCODING_HEXADECIMAL",
            hashFunction="HASH_FUNCTION_KECCAK256",
        )


class WhoAmI(BaseModel):
    userId: uuid.UUID
    username: str
    organizationId: uuid.UUID
    organizationName: str


class TurnkeyClient:
    ENDPOINT = "https://api.turnkey.com"

    def __init__(self):
        # Do dependency injection here
        WalletAccount._client = self

    @cached_property
    def org_id(self) -> str:
        if not (org_id := os.environ.get("TURNKEY_ORGANIZATION_ID")):
            raise ClientError("Must specify `TURNKEY_ORGANIZATION_ID`")

        return org_id

    @cached_property
    def _public_key(self) -> str:
        if not (pubkey := os.environ.get("TURNKEY_API_PUBLIC_KEY")):
            raise ClientError("Must specify `TURNKEY_API_PUBLIC_KEY`")

        return pubkey

    @cached_property
    def __private_key(self):
        if not (pkey := os.environ.get("TURNKEY_API_PRIVATE_KEY")):
            raise ClientError("Must specify `TURNKEY_API_PRIVATE_KEY`")

        return ec.derive_private_key(int(pkey, 16), ec.SECP256R1())

    def post(self, endpoint: str, **payload) -> dict:
        # Add global stuff
        payload["organizationId"] = self.org_id

        # Encode payload
        payload_str = json.dumps(payload)
        signature = self.__private_key.sign(payload_str.encode(), ec.ECDSA(hashes.SHA256()))
        # Create stamp
        stamp = {
            "publicKey": self._public_key,
            "scheme": "SIGNATURE_SCHEME_TK_API_P256",
            "signature": signature.hex(),
        }
        encoded_stamp = urlsafe_b64encode(json.dumps(stamp).encode()).decode().rstrip("=")

        response = requests.post(
            f"{self.ENDPOINT}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "X-Stamp": encoded_stamp,
            },
            data=payload_str,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as e:
            raise ClientError(response.json()["message"]) from e

        return response.json()

    def get_users(self) -> list[User]:
        result = self.post("/public/v1/query/list_users")
        return list(map(User.model_validate, result["users"]))

    def create_wallet(
        self,
        name: str,
        *accounts: AccountSpec,
        mnemonic_length: int = 12,
    ) -> uuid.UUID:
        if mnemonic_length not in (12, 15, 18, 21, 24):
            raise ClientError(f"Invalid mnemonic length '{mnemonic_length}'.")

        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        result = self.post(
            "/public/v1/submit/create_wallet",
            type=str(ActivityType.CREATE_WALLET),
            timestampMs=str(timestamp_ms),
            parameters=dict(
                walletName=name,
                accounts=[account.model_dump(mode="json", by_alias=True) for account in accounts],
                mnemonicLength=mnemonic_length,
            ),
        )

        return uuid.UUID(result["activity"]["result"]["createWalletResult"]["walletId"])

    def get_wallets(self) -> list[Wallet]:
        result = self.post("/public/v1/query/list_wallets")
        return list(map(Wallet.model_validate, result["wallets"]))

    def get_wallet_accounts(self, wallet_id: uuid.UUID) -> list[WalletAccount]:
        result = self.post("/public/v1/query/list_wallet_accounts", walletId=str(wallet_id))
        return list(map(WalletAccount.model_validate, result["accounts"]))

    def sign_raw_payload(self, **parameters) -> dict:
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        result = self.post(
            "/public/v1/submit/sign_raw_payload",
            type=str(ActivityType.SIGN_RAW_PAYLOAD_V2),
            timestampMs=str(timestamp_ms),
            parameters=parameters,
        )
        return result["activity"]["result"]["signRawPayloadResult"]

    def whoami(self) -> WhoAmI:
        result = self.post("/public/v1/query/whoami")
        return WhoAmI.model_validate(result)
