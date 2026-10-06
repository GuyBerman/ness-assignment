# eBay automation exercise

Playwright + Python. The scenario searches eBay for items under a price, adds them to the cart, and checks that the cart total stays within budget.

## How to run

Prerequisites:
- Python 3.11 or newer
- Google Chrome (eBay blocks Playwright's bundled Chromium, so the tests use the installed Chrome)

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run:

```bash
pytest tests/unit                       # offline tests
pytest tests/e2e                        # full scenario on eBay, all rows in data/search_cases.yaml
pytest tests/e2e -k shoes_under_220     # a single row
```

eBay sometimes shows a captcha. When it does, the test waits up to two minutes for you to solve it in the browser window and then continues. To avoid this on every run, save a session once and the tests will reuse it:

```bash
python scripts/save_session.py
```

Test inputs are in `data/search_cases.yaml`. Settings are in `config/default.yaml`. A profile from `config/profiles/` can override them (`ENV=ci pytest ...`), and so can `EBAY_*` environment variables (for example `EBAY_CURRENCY=USD`).

## Architecture

```
tests/            test scenario and fixtures
src/ebay_automation/
  flows/          the four functions from the assignment: login, search, add to cart, cart total check
  pages/          page objects: home, login, search results, item, cart
  components/     parts shared between pages: search box, price filter, paging, result card, variant picker
  core/           base page and component classes, bot-page detection
  config/         settings loader
  models/         price and test-data models
  utils/          price parsing, URL helpers, report attachments
config/           settings and profiles
data/             test inputs
```

Tests call the flows. Flows use page objects. Page objects hold the locators and page actions. Tests don't contain locators, and pages don't contain assertions.

## Limitations and assumptions

- Login: the tests run as a guest, since eBay allows a guest cart. Logging in with a username and password is implemented, but eBay usually shows a captcha there. To run logged in, sign in once by hand with `python scripts/save_session.py --login` and set `EBAY_AUTH__MODE=storage_state`.
- Currency: eBay picks the currency from your location. From Israel prices show in ILS, so a max price of 220 means ILS 220. Change `currency` in the config if you run from somewhere else.
- Cart total: the check uses the cart's "Items" line, which is item prices only. eBay's "Subtotal" line includes shipping, and the search price filter ignores shipping. Set `cart.compare_field: subtotal` to include it.
- Quantity stays 1. Size and color are picked at random. A random quantity would multiply the price and break the budget check.
- The threshold uses the number of items actually added, which is the same as `urls.length` unless a listing couldn't be added.
- eBay blocks headless browsers and sometimes blocks automated Chrome too, with a "Something went wrong" page. The test clicks "Go to homepage" and retries. If eBay keeps blocking, the test is marked as skipped. Waiting a while or switching network usually helps.
- Results come from live listings, so they differ between runs.

## Run report

A full run against eBay (51 tests, all passed) is in `docs/run-report/`:
- `report.html`: HTML report, opens in a browser
- `allure-report/`: Allure report
- `junit.xml`: JUnit XML
- `screenshots/`: a screenshot for each item added to the cart and for each cart page

Each run writes new reports to `reports/`.
