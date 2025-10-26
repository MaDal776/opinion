# Troubleshooting

Solutions to common issues when using the Opinion CLOB SDK.

### Installation Issues

#### ImportError: No module named 'opinion\_clob\_sdk'

**Problem:**

```python
import opinion_clob_sdk
# ModuleNotFoundError: No module named 'opinion_clob_sdk'
```

**Solutions:**

1. **Install the SDK:**

   ```bash
   pip install opinion_clob_sdk
   ```
2. **Verify installation:**

   ```bash
   pip list | grep opinion
   python -c "import opinion_clob_sdk; print(opinion_clob_sdk.__version__)"
   ```
3. **Check Python environment:**

   ```bash
   which python  # Ensure correct Python interpreter
   which pip     # Ensure pip matches Python
   ```
4. **Use virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install opinion_clob_sdk
   ```

***

#### Dependency Conflicts

**Problem:**

```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
This behaviour is the source of the following dependency conflicts.
```

**Solutions:**

1. **Create fresh virtual environment:**

   ```bash
   python3 -m venv fresh_env
   source fresh_env/bin/activate
   pip install opinion_clob_sdk
   ```
2. **Upgrade pip:**

   ```bash
   pip install --upgrade pip setuptools wheel
   ```
3. **Force reinstall:**

   ```bash
   pip install --force-reinstall opinion_clob_sdk
   ```

***

### Configuration Issues

#### InvalidParamError: chain\_id must be 56

**Problem:**

```python
client = Client(chain_id=1, ...)
# InvalidParamError: chain_id must be 56
```

**Solution:** Use BNB Chain Mainnet 56

```python
# ✓ BNB CHain Mainnet
client = Client(
    chain_id=56,
    rpc_url='___',
    ...
)
```

***

#### Missing Environment Variables

**Problem:**

```python
apikey=os.getenv('API_KEY')
# TypeError: Client.__init__() argument 'apikey' must be str, not None
```

**Solutions:**

1. **Create `.env` file:**

   ```bash
   # .env
   API_KEY=your_api_key_here
   RPC_URL=___
   PRIVATE_KEY=0x...
   MULTI_SIG_ADDRESS=0x...
   ```
2. **Load environment variables:**

   ```python
   from dotenv import load_dotenv
   import os

   load_dotenv()  # Load .env file

   # Verify loaded
   print(os.getenv('API_KEY'))  # Should not be None
   ```
3. **Provide defaults:**

   ```python
   apikey = os.getenv('API_KEY')
   if not apikey:
       raise ValueError("API_KEY environment variable not set")
   ```

***

### API Errors

#### OpenApiError: errno != 0

**Problem:**

```python
response = client.get_market(99999)
if response.errno != 0:
    print(response.errmsg)  # "Market not found"
```

**Solutions:**

1. **Always check errno:**

   ```python
   response = client.get_market(market_id)

   if response.errno == 0:
       # Success
       market = response.result.data
   else:
       # Handle error
       print(f"Error {response.errno}: {response.errmsg}")
   ```
2. **Common errno codes:**

   | Code | Meaning      | Solution                       |
   | ---- | ------------ | ------------------------------ |
   | 0    | Success      | Proceed with result            |
   | 404  | Not found    | Check ID exists                |
   | 400  | Bad request  | Check parameters               |
   | 401  | Unauthorized | Check API key                  |
   | 500  | Server error | Retry later or contact support |
3. **Wrap in try-except:**

   ```python
   try:
       response = client.get_market(market_id)
       if response.errno == 0:
           market = response.result.data
       else:
           logging.error(f"API error: {response.errmsg}")
   except OpenApiError as e:
       logging.error(f"API communication error: {e}")
   ```

***

### InvalidParamError: market\_id is required

**Problem:**

```python
client.get_market(market_id=None)
# InvalidParamError: market_id is required
```

**Solution:** Always provide required parameters:

```python
# ✗ Bad
market = client.get_market(None)

# ✓ Good
market_id = 123
if market_id:
    market = client.get_market(market_id)
```

***

### Trading Errors

#### InvalidParamError: Price must be positive for limit orders

**Problem:**

```python
order = PlaceOrderDataInput(
    orderType=LIMIT_ORDER,
    price="0",  # ✗ Invalid for limit orders
    ...
)
```

**Solution:** Set valid price for limit orders:

```python
# ✓ Limit order with price
order = PlaceOrderDataInput(
    orderType=LIMIT_ORDER,
    price="0.55",  # Must be > 0
    ...
)

# ✓ Market order with price = 0
order = PlaceOrderDataInput(
    orderType=MARKET_ORDER,
    price="0",  # OK for market orders
    ...
)
```

***

#### InvalidParamError: makerAmountInBaseToken is not allowed for market buy

**Problem:**

```python
order = PlaceOrderDataInput(
    side=OrderSide.BUY,
    orderType=MARKET_ORDER,
    makerAmountInBaseToken="100"  # ✗ Not allowed
)
```

**Solution:** Use correct amount field:

**Market BUY:**

```python
# ✓ Use makerAmountInQuoteToken
order = PlaceOrderDataInput(
    side=OrderSide.BUY,
    orderType=MARKET_ORDER,
    price="0",
    makerAmountInQuoteToken="100"  # ✓ Spend 100 USDT
)
```

**Market SELL:**

```python
# ✓ Use makerAmountInBaseToken
order = PlaceOrderDataInput(
    side=OrderSide.SELL,
    orderType=MARKET_ORDER,
    price="0",
    makerAmountInBaseToken="50"  # ✓ Sell 50 tokens
)
```

***

#### InvalidParamError: makerAmountInQuoteToken must be at least 1

**Problem:**

```python
order = PlaceOrderDataInput(
    makerAmountInQuoteToken="0.5",  # ✗ Below minimum
    ...
)
```

**Solution:** Use minimum amount of 1:

```python
# ✓ Minimum amounts
order = PlaceOrderDataInput(
    makerAmountInQuoteToken="1",  # ✓ At least 1 USDT
    # or
    makerAmountInBaseToken="1",   # ✓ At least 1 token
    ...
)
```

### Blockchain Errors

#### BalanceNotEnough

**Problem:**

```python
client.split(market_id=123, amount=100_000000)
# BalanceNotEnough: Insufficient balance for operation
```

**Solutions:**

1. **Check balance:**

   ```python
   balances = client.get_my_balances().result.data
   usdt = next((b for b in balances if 'usdt' in b.token.lower()), None)

   if usdt:
       balance_wei = int(usdt.amount)
       balance_usdt = balance_wei / 1e6  # Convert from wei
       print(f"USDT balance: ${balance_usdt}")

       amount_to_split = 10 * 1e18  # 10 USDT
       if balance_wei >= amount_to_split:
           client.split(market_id=123, amount=int(amount_to_split))
       else:
           print("Insufficient balance")
   ```
2. **For merge - need both outcome tokens:**

   ```python
   positions = client.get_my_positions().result.list
   yes_pos = next((p for p in positions if p.token_id == 'token_yes'), None)
   no_pos = next((p for p in positions if p.token_id == 'token_no'), None)

   if yes_pos and no_pos:
       # Can only merge min of both
       merge_amount = min(int(yes_pos.amount), int(no_pos.amount))
       client.merge(market_id=123, amount=merge_amount)
   ```

***

#### InsufficientGasBalance

**Problem:**

```python
client.enable_trading()
# InsufficientGasBalance: Not enough ETH for gas fees
```

**Solution:** Add ETH to signer wallet:

```python
# 1. Check signer address
signer_addr = client.contract_caller.signer.address()
print(f"Signer address: {signer_addr}")

# 2. Check ETH balance
from web3 import Web3
w3 = Web3(Web3.HTTPProvider(rpc_url))
balance = w3.eth.get_balance(signer_addr)
balance_eth = balance / 1e18

print(f"BNB balance: {balance_bnb}")

# 3. If balance low, send BNB to signer_addr
# Usually $1-5 worth of BNB is enough for many transactions
```

***

**Problem:**

```bash
web3.exceptions.ContractLogicError: execution reverted
```

**Common Causes:**

1. **Insufficient approval:**

   ```python
   # Solution: Enable trading
   client.enable_trading()
   # Then retry operation
   ```
2. **Insufficient balance:** Check balance before operation (see BalanceNotEnough above)
3. **Gas price too low:**

   ```python
   # Usually handled automatically
   # If issues persist, try increasing gas
   ```
4. **Contract state changed:**

   ```python
   # Market may have resolved or status changed
   # Refresh market data
   market = client.get_market(market_id, use_cache=False)
   ```

***

### Performance Issues

#### Too Many API Calls

**Problem:** Hitting rate limits.

**Solutions:**

1. **Use caching:**

   ```python
   # Don't disable cache unless necessary
   client = Client(market_cache_ttl=300, ...)  # Enable caching
   ```
2. **Fetch once, use multiple times:**

   ```python
   # ✗ Bad: Multiple calls for same data
   for i in range(10):
       market = client.get_market(123)
       process(market)

   # ✓ Good: Fetch once
   market = client.get_market(123)
   for i in range(10):
       process(market)
   ```
3. **Paginate efficiently:**

   ```python
   # Fetch all markets efficiently
   all_markets = []
   page = 1
   limit = 20  # Max allowed

   while True:
       response = client.get_markets(page=page, limit=limit)
       if response.errno != 0:
           break

       markets = response.result.list
       all_markets.extend(markets)

       if len(markets) < limit:  # Last page
           break

       page += 1
   ```

***

### Data Issues

#### Precision Errors

**Problem:**

```python
amount = 10.5 * 1e18  # Float precision issues
# 105000000000000000000.0 instead of exact 105000000000000000000
```

**Solution:** Use `safe_amount_to_wei()`:

```python
from opinion_clob_sdk.sdk import safe_amount_to_wei

# ✓ Exact conversion using Decimal
amount_wei = safe_amount_to_wei(10.5, 18)  # Returns int: 105000000000000000000

client.split(market_id=123, amount=amount_wei)
```

***

#### Type Mismatch

**Problem:**

```python
order = PlaceOrderDataInput(
    price=0.55,  # ✗ Float instead of string
    ...
)
```

**Solution:** Use correct types:

```python
# ✓ Correct types
order = PlaceOrderDataInput(
    marketId=123,              # int
    tokenId="token_yes",       # str
    side=OrderSide.BUY,        # int (enum)
    orderType=LIMIT_ORDER,     # int
    price="0.55",              # str ✓
    makerAmountInQuoteToken="100"  # str
)
```

***

### Authentication Issues

#### 401 Unauthorized

**Problem:**

```
HTTPError: 401 Client Error: Unauthorized
```

**Solutions:**

1. **Check API key:**

   ```python
   import os
   apikey = os.getenv('API_KEY')
   print(f"API Key: {apikey[:10]}...")  # Print first 10 chars

   if not apikey or apikey == 'your_api_key_here':
       print("Invalid API key")
   ```
2. **Verify key format:**

   ```python
   # Should look like:
   # opn_prod_abc123xyz789 (production)
   # opn_dev_abc123xyz789 (development)
   ```
3. **Contact support:** If key is correct but still failing, contact <nik@opinionlabs.xyz>

***

#### Private Key Issues

**Problem:**

```
ValueError: Private key must be exactly 32 bytes long
```

**Solutions:**

1. **Check format:**

   ```python
   # ✓ Valid formats
   private_key = "0x1234567890abcdef..."  # With 0x prefix (64 hex chars)
   private_key = "1234567890abcdef..."    # Without 0x prefix (64 hex chars)

   # ✗ Invalid
   private_key = "0x123"  # Too short
   private_key = 12345    # Not a string
   ```
2. **Verify length:**

   ```python
   pk = os.getenv('PRIVATE_KEY')
   if pk.startswith('0x'):
       pk = pk[2:]  # Remove 0x prefix

   if len(pk) != 64:
       print(f"Invalid private key length: {len(pk)} (expected 64)")
   ```

***

### Debug Tips

#### Enable Logging

```python
import logging

# Set to DEBUG for detailed logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all SDK operations will log details
client = Client(...)
```

#### Inspect Responses

```python
import json

response = client.get_market(123)

# Pretty print response
print(json.dumps(response.to_dict(), indent=2))
```

#### Check SDK Version

```python
import opinion_clob_sdk
print(f"SDK Version: {opinion_clob_sdk.__version__}")

# Check dependencies
import web3
import eth_account
print(f"Web3 version: {web3.__version__}")
print(f"eth_account version: {eth_account.__version__}")
```

#### Verify Network Connection

```python
# Test RPC connection
from web3 import Web3

w3 = Web3(Web3.HTTPProvider(rpc_url))
print(f"Connected: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Latest block: {w3.eth.block_number}")
```

***

### Getting Help

If you're still experiencing issues:

1. **Check FAQ:** Frequently Asked Questions
2. **Email Support:** <nik@opinionlabs.xyz>

When reporting issues, include:

* SDK version
* Python version
* Full error traceback
* Minimal code to reproduce
* Expected vs actual behavior