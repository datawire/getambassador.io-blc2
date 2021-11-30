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

or

```shell
TARGET=~/src/getambassador.io PRODUCT=getambassadorio USER_AGENT=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36 make -C ~/src/blc2 > blc.log
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
 - `USER_AGENT` (default: `github.com/datawire/getambassador.io-blc2`; not required to be set):
    + Specifies the `User_Agent` header value for each request. It avoids security blocks from external sites

# Why

Why this is better than other broken link checkers (at least better
than https://github.com/stevenvachon/broken-link-checker):

 - It does a better job of implementing the low-level fundamentals:
   - It uses caching to avoid fetching the same resource twice.
   - It understands HTTP 429 / Retry-After to back off and try again
     later, and does this without blocking other pages from being
     checked.
   - It checks that the `#fragment` exists in the linked page.
   - It checks more than just HTML:
      + It understands many link types in HTML
      + It understands sourcemap v3 links in JavaScript
      + It understands Babel/WebPack(?) `/!* For license information
        please see … */` links in JavaScript.
      + It understands `url(…)` references in CSS.
      + That said, it could do even better; search for "TODO" in
        `blclib/checker.py`.

 - It does a better job of handling practical concerns:
   - Given a directory of a static website, it can identify pages that
     are not linked to by any other page, flagging that as a problem.
   - For Netlify sites, it understands Netlify's special files, so it
     can quickly run against a local directory of static files, rather
     than having to actually deploy to Netlify and check the pages
     with slow over-the-network requests.

 - It does a better job of letting you address your own high-level
   business-logic needs:
   - It is easy to extend with your own business logic and
     site-specific checks, such as
      + Extra validation on the HTML, like "pages must have canonical
        links" (example: `generic_blc.py:handle_html_extra`)
      + Extra checks on links to detect links that are semantically
        broken even if they're not technicaly broken (links that are
        "ugly") (example:
        `getambassadorio_blc.py:product_ugly_check`).
      + Special handling for sites that implement fragments via
        JavaScript (*cough*GitHub*cough*) (example:
        `generic_blc.py:handle_link`).

In short:
 + It is faster
 + It checks links more thoroughly
 + It gives you tools to address false positives
 + It lets you add your own semantic checks

# Dependencies

- GNU Make
- `date`
- `python3`
- `node` `>=15.0.0`
- `yarn` `^v1.3.2`
