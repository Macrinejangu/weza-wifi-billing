WEZA-61: Wi-Fi Session States

Session States

State Description
PENDING_PAYMENT Waiting for payment confirmation.
PAYMENT_CONFIRMED Payment successfully verified.
ACTIVATING Internet access is being activated.
ACTIVE Internet access is available and the timer is running.
EXPIRED Purchased internet time has ended.
FAILED Payment or activation failed.
CANCELLED Session was cancelled before activation.

Session Flow

PENDING_PAYMENT → PAYMENT_CONFIRMED → ACTIVATING → ACTIVE → EXPIRED

A session can also become FAILED or CANCELLED.

Business Rules

1. Verify payment before activating internet access.
2. Start the timer only after successful activation.
3. Failed activation must not consume purchased time.
4. Prevent duplicate sessions from repeated payment callbacks.
5. Disconnect access when a session expires.
6. Expired or disconnected sessions must not remain active.
7. Failed activation must not consume the customer's purchased time.


Pending Decisions

- Router integration and activation verification.
- Activation retries and payment recovery.
- Hotspot and PPPoE session handling.
