# Bundled Telegram provider

Copied from the working tree of `/Users/yuhangan/enoch/libraries/telegram`
(branch `yuhang/shop-feature`, HEAD `a34390a`) for OneAgent's shop feature.
This is agent-neutral provider code, licensed under the repository's Apache-2.0
license. It adds explicit card breaks and product-table splitting for individual
Telegram previews.

OneAgent loads this source via `genesis.toml` and carries it in `body_paths`.
The standalone provider can also be installed with:

```bash
python -m pip install ./libraries/telegram
```

Its regression tests run as part of OneAgent's test suite through
`tests/test_oneagent_shop_telegram.py`.
