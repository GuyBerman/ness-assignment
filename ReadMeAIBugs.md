# Review of the AI-generated test

The original code:

```python
from playwright.sync_api import sync_playwright
from selenium import webdriver
import time

def test_search_functionality():
    browser = sync_playwright().start().chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")

    time.sleep(2)

    search_box = page.locator("#search")
    search_box.fill("playwright testing")

    page.locator(".button").click()

    time.sleep(3)

    results = page.locator(".result-item")

    browser.close()
```

## 1. The test has no assertion

```python
results = page.locator(".result-item")
```

A locator in Playwright is lazy: creating it doesn't look at the page at all. Nothing is checked, so the test passes as long as no exception is thrown, even if the search returned nothing. That's the most serious problem, because the test can never catch a bug.

Fix:

```python
from playwright.sync_api import expect

results = page.locator(".result-item")
expect(results.first).to_be_visible()
expect(results).not_to_have_count(0)
```

## 2. Unused Selenium import

```python
from selenium import webdriver
```

It's never used, and it mixes two different automation tools. If Selenium isn't installed, the file fails to import and the test doesn't run at all.

Fix: delete the line.

## 3. Playwright is never stopped, and the browser isn't closed on failure

```python
browser = sync_playwright().start().chromium.launch()
...
browser.close()
```

The object returned by `start()` is thrown away, so `stop()` can never be called and the Playwright process is left running. `browser.close()` only runs if every line before it succeeds. When a step fails, the browser stays open, and on a CI machine those processes pile up.

Fix: use a context manager, or better, the `page` fixture from pytest-playwright, which opens and closes everything for each test:

```python
with sync_playwright() as p:
    browser = p.chromium.launch()
    try:
        page = browser.new_page()
        ...
    finally:
        browser.close()
```

## 4. Fixed `time.sleep()` waits

```python
time.sleep(2)
time.sleep(3)
```

A fixed wait is too long when the page is fast, which wastes time on every run, and too short when the page is slow, which makes the test fail at random. Playwright already waits for elements before `fill()` and `click()`.

Fix: remove the sleeps, and wait for a condition where one is needed:

```python
expect(page.locator(".result-item").first).to_be_visible()
```

## 5. Weak locators and the wrong URL

```python
page.goto("https://example.com")
page.locator(".button").click()
```

`example.com` is a placeholder page with no search box, so `fill()` waits 30 seconds and fails. `.button` is a generic CSS class. If it matches more than one element, Playwright raises a strict mode error; if it matches one, it may be the wrong button. The URL and search text are also hard-coded in the test.

Fix: use the real site from config, and locate elements by role or by what the user sees:

```python
page.goto(base_url)
search_box = page.get_by_role("searchbox")
search_box.fill("playwright testing")
search_box.press("Enter")   # or: page.get_by_role("button", name="Search").click()
```

## Corrected version

```python
from playwright.sync_api import Page, expect


def test_search_returns_results(page: Page, base_url: str) -> None:
    page.goto(base_url)

    search_box = page.get_by_role("searchbox")
    search_box.fill("playwright testing")
    search_box.press("Enter")

    results = page.locator(".result-item")
    expect(results.first).to_be_visible()
    expect(results).not_to_have_count(0)
```

The `page` fixture handles opening and closing the browser, and `base_url` comes from config (`pytest --base-url ...`).
