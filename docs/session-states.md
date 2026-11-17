# Wi-Fi session states

The mock demo records a purchase as `pending` until a simulated payment succeeds. A successful payment changes the purchase to `paid`. A failed payment attempt leaves the purchase pending for another attempt.

A successful payment creates at most one session. The session starts at `PAYMENT_CONFIRMED` with activation status `not_started` and no timer. Activation records an attempt and transitions through `ACTIVATING`. Simulated router confirmation moves the session to `ACTIVE` with activation status `succeeded` and sets the timestamps. The timer uses the duration captured at purchase time.

A failed activation moves the session to `FAILED` with activation status `failed` and leaves the timer unset. The demo permits another activation attempt. Repeating activation after success returns the existing session and its original timestamps.

The model reserves `PENDING_PAYMENT`, `EXPIRED` and `CANCELLED` for future flows. Expiry enforcement, disconnection, live router activation, payment recovery and hotspot or PPPoE policy are pending.
