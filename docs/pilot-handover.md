# Weza Wi-Fi pilot handover

## Start a clean local pilot

1. Install the dependencies and start a disposable PostgreSQL database using the [README](../README.md). The [database guide](database-decision.md) also covers an existing local PostgreSQL installation.
2. In the private root `.env`, set a fresh random `JWT_SECRET` of at least 32 characters. Set `ROUTER_MODE=mock` and `ENABLE_MOCK_PAYMENTS=true`. Keep `ENABLE_DARAJA_SANDBOX_PAYMENTS=false` and `ENABLE_DIRECT_HOTSPOT_CHECKOUT=false`.
3. With the backend environment active, run these from `backend/`.

   ```sh
   python -m alembic upgrade head
   python -m alembic current
   python -m app.create_staff
   ```

   Expect one migration head, `0013_admin_network_state` on this release. Create an admin and repeat `python -m app.create_staff` for a separate operator. Use test accounts and keep passwords private.
4. Start the API and both portals using the README. Set `VITE_API_BASE_URL=http://127.0.0.1:8000` in each app's `.env.development.local`. Leave demo data off.
5. Sign in as admin, open Packages, and create a short test hotspot package. Find its ID in the package list. In the customer app's `.env.development.local`, set `VITE_ENABLE_MOCK_CHECKOUT=true` and set `VITE_SANDBOX_PACKAGE_ID` to the package ID. Restart the customer app.
6. In another terminal, activate the same Python environment and run `python -m app.expire_sessions` from `backend/`. Keep the process running throughout the test.

## Record the acceptance checks

| Check | Expected result |
| --- | --- |
| Open the package page, choose the test plan, and follow the sign-in link to Create an account. | A new customer registers and signs in. Checkout returns to the selected plan. |
| Pay with a fictional number in simulated checkout. View payment and connection status. | Both screens identify the simulation. The countdown starts at payment confirmation. Staff find the same payment and session. |
| Change the plan's price or duration as admin while the customer has an active plan. | The existing purchase keeps its original terms. A later purchase uses the new terms. |
| Wait for the paid time to end. Buy the test plan again. | The first session is expired. A second purchase has its own payment and countdown. |
| Sign in as an operator and open Packages. Then deactivate the test package as admin. | Operators are read-only. The customer catalogue removes the deactivated package. The admin activity log records the change. |
| Edit an answer under System Settings → Customer Support Answers. Reopen Support as a customer. | The guided chat shows the saved question and answer. The activity log names the administrator who made the edit. |
| Run `python -m pytest -q tests/test_pilot_journey.py tests/test_pilot_management.py` from `backend/` with `TEST_DATABASE_URL` pointing to a migrated disposable database and `ROUTER_MODE=mock`. | The cases cover delayed activation and staff retry, including reuse of the existing payment and expiry time. |

## Before client acceptance

- Ask a second teammate to run the guide on a clean checkout. Record the commit, who ran the checks, and the result for each check.
- Run a separate Daraja test payment through the isolated MikroTik. On the lab machine only, set `ROUTER_MODE=mikrotik` and `ALLOW_SANDBOX_ROUTER_ACTIVATION=true` in the root `.env` or the shell. Without both, a sandbox payment cannot open the router: activation is refused and the session shows as failed. Confirm usable internet, speed, reconnect, expiry, and staff recovery. Record only the evidence needed to reproduce the test, then set the override back to `false`.
- Confirm the support contact and who owns escalation. The guided chat provides saved answers. The support contact placeholder stays visible until approved contact details are supplied.
- Confirm who accepts the handover, where the app will run, and who owns the API, expiry process, database backup, and router settings.
- Before any rollout, take a database backup and verify a restore on a spare database. Record the release commit and schema revision. If a release must be reversed, follow the tested rollback procedure for the app and database together. Preserve customer and payment records.

Use the simulated run to demonstrate the software and record the separate outcome of the router and payment-provider checks. Production payments need a separately approved setup.
