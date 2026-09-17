# Claiming the prize, once `oracle.py` prints MATCH

Written ahead of a MATCH so that nothing has to be worked out under time
pressure. **Do not run any of this against a candidate the oracle has not
confirmed.**

## 0. Confirm the key

```bash
python3 tools/oracle.py --selftest        # must print SELFTEST OK first
python3 tools/oracle.py "<64 hex chars>"  # must print MATCH
```

`--selftest` certifies the transform against Puzzle #1's published answer. A
MATCH on your candidate means the key derives to
`0x1fa8Be9De5bBFE047C72dB8E8E3257128F7661ad`, the escrow holding 0.05 ETH.

## 1. Check the prize is still there before doing anything else

```
https://etherscan.io/address/0x1fa8Be9De5bBFE047C72dB8E8E3257128F7661ad
```

Expect: balance 0.05 ETH, nonce 0, one incoming transaction from
`0x0a937ec94abc55d92f5740a988a122ebdcab2e15`, none outgoing. If the nonce is no
longer 0, someone has already swept it and there is nothing to claim.

## 2. Sweep it, and sweep it in one transaction

This key is public the moment it exists anywhere outside your own machine.
Anyone watching the mempool can and will front-run a slow claim, so:

1. **Never paste the key into a website, a wallet extension, a Discord, or any
   "sweeper" tool.** Sign locally.
2. **Do not fund the escrow address with gas.** A funding transaction announces
   the key's existence and invites a front-run. Puzzle-key addresses are
   watched precisely for that pattern.
3. Send the **entire balance minus gas** to an address you already control, in a
   single signed transaction, built offline and broadcast once.

The account has 0.05 ETH and needs 21,000 gas for a plain transfer, so the
transferable amount is `0.05 ETH - 21000 * gasPrice`. At 20 gwei that is about
0.00042 ETH of gas; the rest is yours. Use a **private transaction relay**
(Flashbots Protect RPC or an equivalent) rather than the public mempool, which
removes the front-running window entirely.

Minimal local sweep, offline signing, broadcast through a private relay:

```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://rpc.flashbots.net/fast"))   # private relay
KEY  = "0x<64 hex>"                       # the confirmed key
TO   = "0x<an address you already control>"
acct = w3.eth.account.from_key(KEY)
bal  = w3.eth.get_balance(acct.address)
tip  = w3.to_wei(2, "gwei")
base = w3.eth.get_block("latest")["baseFeePerGas"]
cap  = base * 2 + tip
tx = {
    "chainId": 1, "to": TO, "nonce": w3.eth.get_transaction_count(acct.address),
    "gas": 21000, "maxFeePerGas": cap, "maxPriorityFeePerGas": tip,
    "value": bal - 21000 * cap,           # everything the gas ceiling allows
}
signed = acct.sign_transaction(tx)
print(w3.eth.send_raw_transaction(signed.raw_transaction).hex())
```

`value = bal - 21000 * maxFeePerGas` (not `* baseFee`) so the transaction stays
valid if the base fee rises before inclusion; the unspent difference is
refunded to you.

## 3. Afterwards

The author never published an address, so there is nobody to notify and no
claim form. Sweeping the escrow *is* the claim. If you want the result on the
record, the upstream project
(`floflo777/open-crypto-puzzles`) takes a solution PR: the folder is
`3-small-prizes/crypto-puzzles-2018-puzzle-2-0-05eth`, and its schema wants the
key, the derived address, the sweep transaction hash, and the reading method.

## Custody note

A raw private key in a file is a bearer instrument. Sweep to an address whose
key you control and have backed up, then delete the puzzle key from disk and
from shell history (`history -c`, and check `~/.bash_history`,
`~/.python_history`, and any editor swap files).
