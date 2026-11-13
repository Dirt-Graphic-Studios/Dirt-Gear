# Dirt Gear Premium

Free users can finish **5 gear sets a day** (Pack & install, Export .pnt or Export TGAs). Re-packing or exporting a gear name that's already been finished today doesn't use another slot. The count resets at local midnight. Premium (**$5 USD/month**) removes the limit.

Everything is switched by `source/premium_config.json`. While `"enabled"` is `false`, there's no limit at all.

```json
{ "enabled": true, "daily_limit": 5, "price": "$5 USD / month",
  "store_id": 12345, "product_ids": [67890],
  "checkout_url": "https://dirtgraphicstudios.lemonsqueezy.com/buy/..." }
```

## Lemon Squeezy setup

1. Create a store at lemonsqueezy.com and finish the payout and identity steps.
2. Add a product called **Dirt Gear Premium**, priced as a **subscription** at $5 USD monthly.
3. In the product, turn on **Generate license keys**. Set the activation limit (3 PCs is sensible) and leave keys tied to the subscription, so they expire when it ends.
4. Copy the **Store ID** (Settings → Stores), the **Product ID** (from the product's menu) and the product's **checkout link** into `premium_config.json`, and set `"enabled": true`.

The app calls the public License API (`/v1/licenses/activate`, `/validate` and `/deactivate`). No API key or server is needed. Keys from another store or product are rejected. A key is re-checked once a day. Without internet, Premium keeps working for 7 days after the last successful check.

## Friend codes

Friend codes (`DGF-XXXX-XXXX-XXXX-XXXX`) unlock Premium for free, offline. Only SHA-256 hashes ship in `source/friend_codes.txt`. To make more:

```
python tools/make_friend_codes.py 10 my-private-codes.txt
```

This appends the hashes, which you commit. Keep the plain codes private and never commit them. To revoke a code, delete its hash line, and it stops working in the next release.

## Honest limits

The source is public, so a technical user could remove the cap from their own copy. It's a fair-use paywall, not DRM.
