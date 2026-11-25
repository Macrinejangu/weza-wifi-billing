# Administrator payment and network checks

Sign in to the staff dashboard as an administrator. The three actions are under Payments and Network & Devices. The server checks the role on each request.

| Action | Local verification | Isolated lab verification |
| --- | --- | --- |
| Manual STK | With mock payments and router mode enabled, select a saved unpaid purchase for a customer with a mobile number. Simulate one prompt. The payment remains pending. A repeat request is blocked. | Disable mock payments, enable Daraja sandbox payments, and set `DARAJA_TEST_PHONE` privately. Use an eligible purchase linked to the approved handset and verified hotspot device. Confirm the test handset receives one prompt. Verify the payment and session separately. |
| Run Ping Sweep | Register a demo router and access points in the demo database. Simulation identifies its results on screen. | Register private management IPs on router and access point records. Run a sweep from a server on the test network. A device which does not answer ICMP is shown as No response. This result leaves the saved inventory status unchanged. |
| Sync Gateway State | Run the simulation and check the identity, hotspot status, and check time are labelled simulated. | Set MikroTik mode and configure the expected router identity. Register the configured host in `routers.host`. Compare the returned identity and hotspot state with the isolated router. Confirm a failed sync preserves the last successful reading. |

Run `python -m alembic upgrade head` from `backend/` before opening the dashboard. Migration `0013_admin_network_state` adds the access point management address and the last verified gateway reading. The sweep covers the first 20 registered routers and 20 registered access points. It accepts only the saved private management addresses. Sync reads the configured router and does not change its settings.

Use a separate database for simulated prompts. The demo does not send a message or settle the simulated pending payment, and a simulated gateway response does not change the saved gateway state.
