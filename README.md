# Usage

```shell
TARGET=~/src/getambassador.io PRODUCT=getambassadorio make -C ~/src/blc2 > blc.log
```

or

```shell
TARGET=~/src/telepresence.io PRODUCT=telepresenceio make -C ~/src/blc2 > blc.log
```

or

```shell
TARGET=~/src/other-thing.tld make -C ~/src/blc2 > blc.log
```

Then `tail blc.log` for a summary, or `grep ^Page blc.log` for a list
of pages with broken links.

# Settings

 - `TARGET` (no default; required to be set):
   + It looks at HTML files in the `${TARGET}/public` directory
   + It obeys redirects in the `${TARGET}/netlify.toml` file (if one
     exists)
 - `PRODUCT` (default=`generic`):
   + Specific per-product link checks settings are defined in
     `${PRODUCT}_blc.py` files.

# Dependencies

- GNU Make
- `date`
- `python3`
- `node` `>=15.0.0`
- `yarn` `^v1.3.2`
