---
name: e2e-test-strategy
description: Design a lean, reliable E2E test suite covering only critical user journeys with Playwright, keeping the suite fast and resilient to CSS changes.
discipline: qa
tags: [testing, e2e, playwright, cypress, selenium]
---

# E2E Test Strategy

## When to use
Apply this skill when deciding what to cover with E2E tests, when an E2E suite is too slow or fragile to trust, when E2E tests break on every CSS or HTML refactor, or when the team is writing E2E tests for features that could be validated at a lower level.

## Signal
- E2E suite takes more than 30 minutes end-to-end in CI.
- E2E tests use CSS selectors (`.btn-primary`, `#checkout-submit`) that break on className changes.
- E2E tests are written for every new feature, regardless of whether lower-level coverage exists.
- E2E suite is retried 3 times in CI to pass.
- E2E tests duplicate what contract tests or integration tests already cover.
- A "quick sanity check" regression test suite takes 45 minutes.

## Why
E2E tests are the most expensive test type: they are slow to run (seconds to minutes per test), slow to write (full environment setup, page models, locator maintenance), and prone to flakiness (network timing, animation timing, third-party load). Their unique value is verifying that the entire stack works together for a real user journey. That value is high for a small number of critical paths but diminishes rapidly when applied to every feature. The 2026 standard: E2E tests should constitute ≤10% of the total test suite and focus exclusively on critical user journeys.

## Remediate

1. **Identify your 5–10 most critical user journeys.** These are the journeys that: (a) represent significant revenue or risk if they break, and (b) cannot be fully verified by contract tests or integration tests because they cross multiple services and involve a real browser. Typical examples:
   - User registration and email verification.
   - Login, logout, session expiry.
   - Product search → add to cart → checkout → payment confirmation.
   - Document upload and processing.
   - Password reset flow.
   Write E2E tests for these journeys. For everything else, rely on unit + integration + contract tests.

2. **Use Playwright as the default tool (June 2026 recommendation).** Playwright advantages over Cypress and Selenium:
   - Accessibility-tree selectors (`getByRole`, `getByText`, `getByLabel`) are resilient to CSS/HTML changes.
   - Native multi-browser support (Chrome, Firefox, Safari/WebKit) in the same API.
   - Built-in parallelism across browsers and test files.
   - Network interception without plugins.
   - Built-in `expect(locator).toBeVisible()` auto-waiting — no explicit `waitFor` needed.

3. **Use accessibility-tree locators, never CSS selectors.** CSS selectors are fragile — they break whenever a designer renames a class. Accessibility-tree selectors describe what the user sees, not the HTML structure:
   ```ts
   // Bad — fragile CSS selector
   await page.click('.btn-primary.checkout-submit');

   // Good — accessibility-tree (resilient to CSS changes)
   await page.getByRole('button', { name: 'Complete Purchase' }).click();
   await page.getByLabel('Email address').fill('user@example.com');
   await page.getByRole('heading', { name: 'Order Confirmed' }).waitFor();
   ```
   This also tests accessibility as a side effect — if the button has no accessible name, the locator fails.

4. **Use the Page Object Model (POM) for reusable page interactions.** Centralize selectors and page interactions in POM classes to avoid duplication across tests:
   ```ts
   class CheckoutPage {
     constructor(private page: Page) {}

     async fillShippingAddress(address: Address) {
       await this.page.getByLabel('Street address').fill(address.street);
       await this.page.getByLabel('City').fill(address.city);
     }

     async submit() {
       await this.page.getByRole('button', { name: 'Place Order' }).click();
     }

     async expectOrderConfirmation() {
       await expect(this.page.getByRole('heading', { name: 'Order Confirmed' })).toBeVisible();
     }
   }
   ```

5. **Run tests in parallel across browsers.** Playwright parallelizes by default across workers. Configure in `playwright.config.ts`:
   ```ts
   export default defineConfig({
     workers: process.env.CI ? 4 : 2,
     projects: [
       { name: 'Chrome', use: { ...devices['Desktop Chrome'] } },
       { name: 'Firefox', use: { ...devices['Desktop Firefox'] } },
       { name: 'Safari', use: { ...devices['Desktop Safari'] } },
       { name: 'Mobile', use: { ...devices['iPhone 14'] } },
     ],
     retries: process.env.CI ? 1 : 0, // only 1 retry — not 3
   });
   ```

6. **Set retries to 1 maximum in CI.** More than 1 retry masks flakiness instead of fixing it. When a test fails twice in CI, investigate the root cause. Apply the flaky-test-quarantine skill if the failure is non-deterministic.

7. **Stub or mock third-party services.** Payment gateways, email providers, and analytics services should be stubbed in E2E tests to: (a) avoid test charges, (b) avoid rate limits, and (c) make tests deterministic:
   ```ts
   await page.route('**/api.stripe.com/**', (route) => {
     route.fulfill({ status: 200, body: JSON.stringify({ status: 'succeeded' }) });
   });
   ```

8. **Do not write E2E tests for things covered by lower-level tests.** If a feature is already covered by: (a) unit tests for business logic, and (b) integration tests for the API endpoint, an E2E test adds maintenance cost without adding unique coverage value. Ask "what would this E2E test catch that the existing tests cannot?" before writing it.

## References
- Playwright documentation (playwright.dev)
- Google Testing Blog — "Just Say No to More End-to-End Tests"
- Martin Fowler — "PageObject" pattern
- DORA State of DevOps Report — test automation recommendations
