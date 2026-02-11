"""
Ethereum Explorer - Flask API Backend
Deploy this on Render.com and connect to your portfolio frontend.
"""

import os
import time
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

app = Flask(__name__)

# ----------------------------------------------------------------------
# CORS — replace "*" with your actual portfolio domain before deploying
# e.g. CORS(app, origins=["https://jorgecastano.com"])
# ----------------------------------------------------------------------
CORS(app, origins="*")

API_KEY = os.getenv("ETHERSCAN_APIKEY")
BASE_URL = "https://api.etherscan.io/v2/api"

# Common ERC-20 tokens to check balances for
COMMON_TOKENS = {
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "DAI":  "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "UNI":  "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
}


# -----------------------------------------------------------------------
# Internal helper
# -----------------------------------------------------------------------

def make_api_call(params: dict) -> dict | None:
    """Call the Etherscan v2 API with rate limiting and error handling."""
    params["chainid"] = "1"
    if API_KEY:
        params["apikey"] = API_KEY

    # Respect rate limits: 0.2s with key, 5s without
    time.sleep(0.2 if API_KEY else 5.0)

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return None
    except Exception as e:
        print(f"API Error: {e}")
        return None


# -----------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------

@app.route("/")
def health_check():
    """Simple health check so Render knows the service is alive."""
    return jsonify({
        "status": "ok",
        "message": "Ethereum Explorer API is running",
        "api_key_loaded": bool(API_KEY)
    })


@app.route("/api/wallet/<address>")
def wallet_lookup(address: str):
    """
    GET /api/wallet/<address>
    Returns ETH balance, recent transactions, token balances, and account type.
    """
    # Validate address format
    if not address.startswith("0x") or len(address) != 42:
        return jsonify({"error": "Invalid address format. Must be 42 characters starting with 0x."}), 400

    result = {}

    # --- ETH Balance ---
    balance_data = make_api_call({
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest"
    })
    if balance_data and balance_data.get("status") == "1":
        result["eth_balance"] = int(balance_data["result"]) / 1e18
    else:
        result["eth_balance"] = None

    # --- Is Contract? ---
    contract_data = make_api_call({
        "module": "contract",
        "action": "getsourcecode",
        "address": address
    })
    is_contract = False
    if contract_data and contract_data.get("status") == "1":
        is_contract = bool(contract_data["result"][0].get("SourceCode"))
    result["is_contract"] = is_contract

    # --- Recent Transactions (last 10) ---
    tx_data = make_api_call({
        "module": "account",
        "action": "txlist",
        "address": address,
        "sort": "desc",
        "page": 1,
        "offset": 10
    })

    transactions = []
    if tx_data and tx_data.get("status") == "1":
        for tx in tx_data["result"]:
            transactions.append({
                "hash":        tx.get("hash"),
                "from":        tx.get("from"),
                "to":          tx.get("to"),
                "value_eth":   int(tx.get("value", "0")) / 1e18,
                "block":       tx.get("blockNumber"),
                "timestamp":   tx.get("timeStamp"),
                "is_outgoing": tx.get("from", "").lower() == address.lower(),
            })
    result["transactions"] = transactions

    # --- Token Balances ---
    token_balances = {}
    for symbol, token_address in COMMON_TOKENS.items():
        token_data = make_api_call({
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": token_address,
            "address": address,
            "tag": "latest"
        })
        if token_data and token_data.get("status") == "1":
            balance = int(token_data["result"]) / 1e18
            if balance > 0:
                token_balances[symbol] = round(balance, 6)

    result["token_balances"] = token_balances

    return jsonify(result)


@app.route("/api/transaction/<tx_hash>")
def transaction_lookup(tx_hash: str):
    """
    GET /api/transaction/<tx_hash>
    Returns full transaction details and receipt (status, gas used, etc).
    """
    # Validate hash format
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return jsonify({"error": "Invalid transaction hash. Must be 66 characters starting with 0x."}), 400

    # --- Transaction Details ---
    tx_data = make_api_call({
        "module": "proxy",
        "action": "eth_getTransactionByHash",
        "txhash": tx_hash
    })

    if not tx_data or not tx_data.get("result"):
        return jsonify({"error": "Transaction not found."}), 404

    tx = tx_data["result"]

    # --- Transaction Receipt ---
    receipt_data = make_api_call({
        "module": "proxy",
        "action": "eth_getTransactionReceipt",
        "txhash": tx_hash
    })
    receipt = receipt_data.get("result") if receipt_data else None

    # Parse values from hex
    value_wei   = int(tx.get("value", "0x0"), 16)
    gas_limit   = int(tx.get("gas", "0x0"), 16)
    gas_price   = int(tx.get("gasPrice", "0x0"), 16)
    block_num   = int(tx.get("blockNumber", "0x0"), 16) if tx.get("blockNumber") else None

    result = {
        "hash":           tx.get("hash"),
        "from":           tx.get("from"),
        "to":             tx.get("to") or "Contract Creation",
        "value_eth":      value_wei / 1e18,
        "value_wei":      value_wei,
        "block":          block_num,
        "gas_limit":      gas_limit,
        "gas_price_gwei": gas_price / 1e9,
        "input_data":     tx.get("input", "0x"),
        "method_id":      tx.get("input", "0x")[:10] if len(tx.get("input", "0x")) > 10 else None,
        "status":         None,
        "gas_used":       None,
        "gas_cost_eth":   None,
    }

    if receipt:
        gas_used = int(receipt.get("gasUsed", "0x0"), 16)
        result["status"]       = "success" if receipt.get("status") == "0x1" else "failed"
        result["gas_used"]     = gas_used
        result["gas_cost_eth"] = (gas_used * gas_price) / 1e18

    return jsonify(result)


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
