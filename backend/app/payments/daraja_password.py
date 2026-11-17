"""The Timestamp and Password fields required by Daraja requests.

Every STK Push and STK Query request carries a Timestamp and a Password.
The Password is base64(shortcode + passkey + timestamp), so it only matches
if the caller uses the SAME timestamp in the request body and in the password.
A mismatch makes Daraja answer "Wrong credentials", so callers must generate
the timestamp once and pass that single value to both places.

Never log the passkey or the password built from it.
"""

import base64
import re
from datetime import datetime, timedelta, timezone


# Kenya is UTC+3 all year, with no daylight saving. 
# A fixed offset avoids depending on the operating system's timezone database, which minimal containers may not include. 
# That Daraja expects Nairobi time is supported by the simulator's behaviour but still to be confirmed by sandbox testing.
EAT = timezone(timedelta(hours=3), "EAT")

_TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"  # YYYYMMDDHHmmss, as Daraja requires

# [0-9] rather than \d: in Python, \d also matches digits from other scripts, which Daraja would reject.
_TIMESTAMP_PATTERN = re.compile(r"[0-9]{14}")


def daraja_timestamp(now: datetime | None=None)->str:
    """Return the current Nairobi time as a 14-digit YYYYMMDDHHmmss string.

    `now` exists so tests can supply a fixed moment. It must be timezone-aware:
    a naive datetime is rejected because guessing its timezone is exactly the
    kind of silent mistake that produces wrong timestamps.
    """
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.utcoffset() is None:
        raise ValueError("now must be timezone-aware.")
    return moment.astimezone(EAT).strftime(_TIMESTAMP_FORMAT)


def build_password(shortcode: str, passkey: str, timestamp: str)-> str:
    """Return base64(shortcode + passkey + timestamp) for a Daraja request.

    Raises ValueError for an empty shortcode or passkey, or a timestamp that
    is not exactly 14 digits, so a wrong password is never built silently.
    """
    if not shortcode or not passkey:
        raise ValueError("shortcode and passkey are required.")
    if _TIMESTAMP_PATTERN.fullmatch(timestamp) is None:
        raise ValueError("timestamp must be 14 digits in YYYYMMDDHHmmss form.")

    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")