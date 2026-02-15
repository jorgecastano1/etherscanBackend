# Ethereum Explorer

A full-stack blockchain explorer for querying Ethereum wallet addresses and transaction hashes in real-time.

## Features

- **Wallet Lookup**: View ETH balance, transaction history, and token holdings (USDC, DAI, WETH, UNI)
- **Transaction Lookup**: Inspect transaction details including gas costs, status, and input data
- **Dark Terminal UI**: Retro-futuristic interface with scanline effects and neon accents
- **Secure Backend**: Python/Flask REST API with rate limiting and CORS protection

## Tech Stack

**Backend:**
- Python 3.x
- Flask (REST API)
- Etherscan API v2
- Deployed on Render

**Frontend:**
- Vanilla JavaScript (Fetch API)
- HTML5/CSS3
- Responsive design

## Live Demo

[View Live](https://jorgecastano1.github.io/Portfolio_Website/etherscan.html)

## Architecture
```
Portfolio Frontend → Flask Backend (Render) → Etherscan API
```

The backend handles API authentication securely while the frontend provides an interactive interface for blockchain data exploration.