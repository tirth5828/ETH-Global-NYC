import os
import time
import requests
from web3 import Web3
from eth_account import Account

CIRCLE_ATTESTATION_API = "https://iris-api.circle.com/v1/attestations"
USDC_ETHEREUM_ADDRESS = Web3.to_checksum_address("0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")  
USDC_BASE_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

# CCTP contract addresses
CCTP = {
    "ETH": {
        "TokenMessenger": Web3.to_checksum_address("0xbd3fa81b58ba92a82136038b25adec7066af3155"),
        "MessageTransmitter": Web3.to_checksum_address("0x0a992d191deec32afe36203ad87d7d289a738f81"),
        "TokenMinter": Web3.to_checksum_address("0xc4922d64a24675e16e1586e3e3aa56c06fabe907"),
        "USDC": USDC_ETHEREUM_ADDRESS
    },
    "BASE": {
        "TokenMessenger": Web3.to_checksum_address("0x1682Ae6375C4E4A97e4B583BC394c861A46D8962"),
        "MessageTransmitter": Web3.to_checksum_address("0xAD09780d193884d503182aD4588450C416D6F9D4"),
        "TokenMinter": Web3.to_checksum_address("0xe45B133ddc64bE80252b0e9c75A8E74EF280eEd6"),
        "USDC": USDC_BASE_ADDRESS
    }
}

# Placeholder ABIs – please replace with actual contract ABIs
USDC_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

TOKEN_MESSENGER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "uint32", "name": "destinationDomain", "type": "uint32"},
            {"internalType": "bytes32", "name": "mintRecipient", "type": "bytes32"},
            {"internalType": "address", "name": "burnToken", "type": "address"}
        ],
        "name": "depositForBurn",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

CCTP_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "burnTxHash", "type": "bytes32"},
            {"internalType": "bytes", "name": "attestation", "type": "bytes"}
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


class GeneralizedCCTP:
    def __init__(self, private_key: str, rpc_urls: dict):
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.w3 = {chain: Web3(Web3.HTTPProvider(url)) for chain, url in rpc_urls.items()}

    def approve_usdc(self, chain: str, amount: int):
        w3 = self.w3[chain]
        usdc = w3.eth.contract(address=CCTP[chain]["USDC"], abi=USDC_ABI)
        messenger = CCTP[chain]["TokenMessenger"]

        # Estimate gas automatically
        estimated_gas = usdc.functions.approve(messenger, amount).estimate_gas({'from': self.address})
        
        # Fetch current fee data
        fee_data = w3.eth.fee_history(1, 'latest', reward_percentiles=[50])
        max_priority_fee = w3.to_wei(2, 'gwei')  # default 2 gwei if fee_history fails
        base_fee = fee_data['baseFeePerGas'][-1] if fee_data['baseFeePerGas'] else w3.to_wei(1, 'gwei')
        max_fee = base_fee + max_priority_fee

        # Build transaction
        tx = usdc.functions.approve(messenger, amount).build_transaction({
            "from": self.address,
            "nonce": w3.eth.get_transaction_count(self.address),
            "gas": estimated_gas,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee
        })

        signed = self.account.sign_transaction(tx)
        
        # Check if wallet balance is enough
        estimated_cost = max_fee * estimated_gas
        balance = w3.eth.get_balance(self.address)
        if balance < estimated_cost:
            raise Exception(f"Insufficient ETH for gas. Balance: {balance}, Estimated cost: {estimated_cost}")

        return w3.eth.send_raw_transaction(signed.raw_transaction).hex()

    def burn_usdc(self, chain: str, amount: int, dest_domain: int, recipient: str):
        w3 = self.w3[chain]
        messenger = w3.eth.contract(address=CCTP[chain]["TokenMessenger"], abi=TOKEN_MESSENGER_ABI)

        # Estimate gas automatically
        burn_tx = messenger.functions.depositForBurn(
            amount,
            dest_domain,
            bytes.fromhex(recipient[2:].zfill(64)),
            CCTP[chain]["USDC"]
        )
        estimated_gas = burn_tx.estimate_gas({'from': self.address})

        # Fetch current fee data
        fee_data = w3.eth.fee_history(1, 'latest', reward_percentiles=[50])
        max_priority_fee = w3.to_wei(2, 'gwei')
        base_fee = fee_data['baseFeePerGas'][-1] if fee_data['baseFeePerGas'] else w3.to_wei(1, 'gwei')
        max_fee = base_fee + max_priority_fee

        tx = burn_tx.build_transaction({
            "from": self.address,
            "nonce": w3.eth.get_transaction_count(self.address),
            "gas": estimated_gas,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee
        })

        signed = self.account.sign_transaction(tx)

        # Check if wallet balance is enough
        estimated_cost = max_fee * estimated_gas
        balance = w3.eth.get_balance(self.address)
        if balance < estimated_cost:
            raise Exception(f"Insufficient ETH for gas. Balance: {balance}, Estimated cost: {estimated_cost}")

        return w3.eth.send_raw_transaction(signed.raw_transaction).hex()

    def get_attestation(self, burn_tx_hash: str):
        while True:
            resp = requests.get(f"{CIRCLE_ATTESTATION_API}/{burn_tx_hash}")
            data = resp.json()
            if data.get("status") == "complete":
                return data["attestation"]
            time.sleep(5)

    def mint_usdc(self, chain: str, burn_tx_hash: str, attestation: str):
        w3 = self.w3[chain]
        minter = w3.eth.contract(address=CCTP[chain]["TokenMinter"], abi=CCTP_ABI)
        tx = minter.functions.mint(burn_tx_hash, attestation).build_transaction({
            "from": self.address,
            "nonce": w3.eth.get_transaction_count(self.address),
            "gas": 300000,
            "maxFeePerGas": w3.to_wei("50", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("2", "gwei")
        })
        signed = self.account.sign_transaction(tx)
        return w3.eth.send_raw_transaction(signed.rawTransaction).hex()
