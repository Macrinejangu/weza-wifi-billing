
import pytest

import app.services.router as router_service


class FakePath:
    def __init__(
        self,
        records,
        on_add=None,
        on_read=None,
        on_remove=None,
        add_returns_empty=False,
    ):
        self.records = records
        self.on_add = on_add
        self.on_read = on_read
        self.on_remove = on_remove
        self.add_returns_empty = add_returns_empty

    def remove(self, *record_ids):
        for record_id in record_ids:
            for record in list(self.records):
                if record.get(".id") == record_id:
                    self.records.remove(record)
                    if self.on_remove:
                        self.on_remove(record)
                    break

    def __iter__(self):
        if self.on_read:
            self.on_read()
        return iter(self.records)

    def add(self, **kwargs):
        record = {**kwargs, ".id": f"*{len(self.records) + 1}"}
        self.records.append(record)

        if self.on_add:
            self.on_add(record)

        return "" if self.add_returns_empty else record[".id"]

    def update(self, **kwargs):
        record_id = kwargs.pop(".id")

        for record in self.records:
            if record.get(".id") == record_id:
                record.update(kwargs)
                return

        raise AssertionError(f"Record {record_id} not found")


class FakeAPI:
    def __init__(
        self,
        active_devices=None,
        hotspot_servers=None,
        simple_queues=None,
        authentication_delay_polls=0,
        empty_profile_add_id=False,
        empty_user_add_id=False,
    ):
        self.empty_profile_add_id = empty_profile_add_id
        self.empty_user_add_id = empty_user_add_id
        self.closed = False
        self.auto_authenticate = active_devices is None
        self.authentication_delay_polls = authentication_delay_polls
        self.active_poll_count = 0
        self.pending_hotspot_user = None

        self.active_devices = (
            [] if active_devices is None else active_devices
        )

        for index, device in enumerate(self.active_devices, start=1):
            device.setdefault(".id", f"*existing-{index}")

        self.initial_active_session_ids = {
            device[".id"] for device in self.active_devices
        }
        self.simple_queues = (
            [] if simple_queues is None else simple_queues
        )

        self.paths = {
            ("system", "identity"): [{"name": "CHR"}],
            ("ip", "hotspot"): (
                hotspot_servers
                if hotspot_servers is not None
                else [
                    {
                        "name": "WEZA-Hotspot-Server",
                        "interface": "ether4",
                        "profile": "WEZA-Hotspot",
                        "disabled": "false",
                    }
                ]
            ),
            ("ip", "hotspot", "user", "profile"): [],
            ("ip", "hotspot", "user"): [],
            ("ip", "hotspot", "active"): self.active_devices,
            ("queue", "simple"): self.simple_queues,
        }

    def _simulate_authentication(self, hotspot_user):
        if not self.auto_authenticate:
            return

        if self.authentication_delay_polls:
            self.pending_hotspot_user = hotspot_user
            return

        self._complete_authentication(hotspot_user)

    def _complete_authentication(self, hotspot_user):
        active_ip = "10.20.0.254"

        self.active_devices.append(
            {
                ".id": f"*active-{len(self.active_devices) + 1}",
                "user": hotspot_user["name"],
                "address": active_ip,
                "server": hotspot_user["server"],
            }
        )

        profiles = self.paths[
            ("ip", "hotspot", "user", "profile")
        ]
        assigned_profile = next(
            profile
            for profile in profiles
            if profile["name"] == hotspot_user["profile"]
        )

        self.simple_queues.append(
            {
                "name": f"<hotspot-{hotspot_user['name']}>",
                "target": f"{active_ip}/32",
                "max-limit": assigned_profile["rate-limit"],
            }
        )

    def _reauthenticate_after_remove(self, active_device):
      if active_device.get(".id") not in self.initial_active_session_ids:
        return

      self.active_devices.append({
        ".id": "*replacement-session",
        "user": active_device["user"],
        "address": active_device["address"],
        "server": active_device["server"],
      })


    def _poll_authentication(self):
        if self.pending_hotspot_user is None:
            return

        self.active_poll_count += 1

        if self.active_poll_count >= self.authentication_delay_polls:
            hotspot_user = self.pending_hotspot_user
            self.pending_hotspot_user = None
            self._complete_authentication(hotspot_user)

    def path(self, *parts):
        records = self.paths[parts]

        if parts == ("ip", "hotspot", "user", "profile"):
            return FakePath(
                records,
                add_returns_empty=self.empty_profile_add_id,
            )

        if parts == ("ip", "hotspot", "user"):
            return FakePath(
                records,
                on_add=self._simulate_authentication,
                add_returns_empty=self.empty_user_add_id,
            )

        if parts == ("ip", "hotspot", "active"):
            return FakePath(
                records,
                on_read=self._poll_authentication,
                on_remove=self._reauthenticate_after_remove,
            )

        return FakePath(records)

    def close(self):
        self.closed = True


@pytest.fixture
def router_settings(monkeypatch):
    monkeypatch.setattr(
        router_service,
        "router_settings",
        lambda: {"expected_identity": "CHR"},
    )


def test_activate_hotspot_device_creates_user_and_speed_profile(
    monkeypatch, router_settings
):
    api = FakeAPI()

    monkeypatch.setattr(router_service, "connect_router", lambda: api)

    # The device must not already be active.
    assert api.active_devices == []

    result = router_service.activate_hotspot_device(
        mac_address="aa-bb-cc-dd-ee-ff",
        download_speed_mbps=5,
        upload_speed_mbps=2,
        ip_address="10.20.0.254",
    )

    assert result["status"] == "ACTIVE"
    assert result["mac_address"] == "AA:BB:CC:DD:EE:FF"
    assert result["rate_limit"] == "2M/5M"
    assert result["download_speed_mbps"] == 5
    assert result["upload_speed_mbps"] == 2

    users = api.paths[("ip", "hotspot", "user")]
    assert len(users) == 1
    assert users[0]["name"] == "AA:BB:CC:DD:EE:FF"
    assert users[0]["profile"] == "WEZA-2M-5M"

    profiles = api.paths[("ip", "hotspot", "user", "profile")]
    assert len(profiles) == 1
    assert profiles[0]["rate-limit"] == "2M/5M"

    # Simulated authentication happened after the user was created.
    assert len(api.active_devices) == 1
    assert api.active_devices[0]["user"] == "AA:BB:CC:DD:EE:FF"

    assert api.closed is True



def test_activation_waits_for_delayed_mac_authentication(
    monkeypatch, router_settings
):
    api = FakeAPI(authentication_delay_polls=3)

    monkeypatch.setattr(router_service, "connect_router", lambda: api)

    result = router_service.activate_hotspot_device(
        mac_address="AA:BB:CC:DD:EE:FF",
        download_speed_mbps=5,
        upload_speed_mbps=2,
        ip_address="10.20.0.254",
    )

    assert result["status"] == "ACTIVE"
    assert api.active_poll_count == 3
    assert len(api.active_devices) == 1
    assert len(api.simple_queues) == 1
    assert api.closed is True


def test_activation_rejects_missing_hotspot_server(
    monkeypatch, router_settings
):
    api = FakeAPI(hotspot_servers=[])

    monkeypatch.setattr(router_service, "connect_router", lambda: api)

    with pytest.raises(router_service.RouterActivationError):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2
        )

    assert api.closed is True


def test_activation_rejects_unconfirmed_active_device(
    monkeypatch, router_settings
):
    # Explicit empty list disables simulated authentication.
    api = FakeAPI(active_devices=[])

    monkeypatch.setattr(router_service, "connect_router", lambda: api)

    with pytest.raises(router_service.RouterActivationError):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2
        )

    assert api.closed is True


def test_authentication_timeout_preserves_user_and_profile_for_late_auth(
    monkeypatch, router_settings
):
    # RouterOS may authenticate after WEZA's polling window has expired.
    # A timeout must therefore not delete the user/profile it could still use.
    api = FakeAPI(active_devices=[])
    monkeypatch.setattr(router_service, "connect_router", lambda: api)

    with pytest.raises(
        router_service.RouterActivationUnconfirmed
    ) as exc_info:
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2
        )

    message = str(exc_info.value)
    assert "authentication was attempted but not confirmed" in message
    assert "Rollback also failed" in message
    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert len(users) == 1
    assert users[0]["name"] == "AA:BB:CC:DD:EE:FF"
    assert users[0]["profile"] == "WEZA-2M-5M"
    assert len(profiles) == 1
    assert profiles[0]["name"] == "WEZA-2M-5M"
    assert api.closed is True


@pytest.mark.parametrize(
    "mac_address",
    [
        "invalid-mac",
        "AA:BB:CC:DD:EE",
        "",
    ],
)
def test_activation_rejects_invalid_mac(mac_address):
    with pytest.raises(ValueError):
        router_service.activate_hotspot_device(
            mac_address, 5, 2
        )


@pytest.mark.parametrize(
    "download_speed, upload_speed",
    [
        (0, 2),
        (5, 0),
        (-1, 2),
        (5, -1),
        (True, 2),
    ],
)
def test_activation_rejects_invalid_speeds(
    download_speed, upload_speed
):
    with pytest.raises(ValueError):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF",
            download_speed,
            upload_speed,
        )


def test_existing_matching_hotspot_session_is_reused_without_changes(
    monkeypatch, router_settings
):
    api = FakeAPI(
        active_devices=[
            {
                ".id": "*old-session",
                "user": "AA:BB:CC:DD:EE:FF",
                "address": "10.20.0.254",
                "server": "WEZA-Hotspot-Server",
            }
        ],
        simple_queues=[
            {
                "name": "<hotspot-AA:BB:CC:DD:EE:FF>",
                "target": "10.20.0.254/32",
                "max-limit": "5M/10M",
            }
        ],
    )

    api.paths[("ip", "hotspot", "user", "profile")].append({
        ".id": "*profile",
        "name": "WEZA-5M-10M",
        "rate-limit": "5M/10M",
    })

    api.paths[("ip", "hotspot", "user")].append({
        ".id": "*existing",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "WEZA-5M-10M",
        "server": "WEZA-Hotspot-Server",
        "disabled": "no",
    })

    monkeypatch.setattr(
        router_service,
        "connect_router",
        lambda: api,
    )

    result = router_service.activate_hotspot_device(
        mac_address="AA:BB:CC:DD:EE:FF",
        download_speed_mbps=10,
        upload_speed_mbps=5,
        ip_address="10.20.0.254",
    )

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert result["status"] == "ACTIVE"
    assert result["rate_limit"] == "5M/10M"
    assert len(users) == 1
    assert users[0][".id"] == "*existing"
    assert users[0]["profile"] == "WEZA-5M-10M"
    assert len(profiles) == 1
    assert profiles[0]["rate-limit"] == "5M/10M"
    assert len(api.active_devices) == 1
    assert api.active_devices[0][".id"] == "*old-session"
    assert len(api.simple_queues) == 1
    assert api.simple_queues[0]["max-limit"] == "5M/10M"


def test_existing_speed_profile_is_reused(
    monkeypatch, router_settings
):
    api = FakeAPI()

    api.paths[("ip", "hotspot", "user", "profile")].append({
        ".id": "*existing",
        "name": "WEZA-5M-10M",
        "rate-limit": "5M/10M",
    })

    monkeypatch.setattr(
        router_service,
        "connect_router",
        lambda: api,
    )

    result = router_service.activate_hotspot_device(
        mac_address="AA:BB:CC:DD:EE:FF",
        download_speed_mbps=10,
        upload_speed_mbps=5,
        ip_address="10.20.0.254",
    )

    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert len(profiles) == 1
    assert profiles[0]["name"] == "WEZA-5M-10M"
    assert profiles[0]["rate-limit"] == "5M/10M"
    assert result["profile"] == "WEZA-5M-10M"


def test_shared_speed_profile_with_wrong_rate_is_not_modified(
    monkeypatch, router_settings
):
    api = FakeAPI()

    original_profile = {
        ".id": "*shared-profile",
        "name": "WEZA-5M-10M",
        "rate-limit": "2M/5M",
    }
    other_customer = {
        ".id": "*other-customer",
        "name": "11:22:33:44:55:66",
        "profile": "WEZA-5M-10M",
        "server": "WEZA-Hotspot-Server",
        "disabled": "no",
    }

    api.paths[("ip", "hotspot", "user", "profile")].append(
        dict(original_profile)
    )
    api.paths[("ip", "hotspot", "user")].append(
        dict(other_customer)
    )

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="existing profiles are immutable",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 10, 5, "10.20.0.254"
        )

    profiles = api.paths[("ip", "hotspot", "user", "profile")]
    users = api.paths[("ip", "hotspot", "user")]

    assert profiles == [original_profile]
    assert users == [other_customer]
    assert api.active_devices == []
    assert api.closed is True


def test_existing_speed_profile_with_wrong_rate_is_rejected_unchanged(
    monkeypatch, router_settings
):
    api = FakeAPI()

    original_profile = {
        ".id": "*existing",
        "name": "WEZA-5M-10M",
        "rate-limit": "2M/5M",
    }
    api.paths[("ip", "hotspot", "user", "profile")].append(
        dict(original_profile)
    )

    monkeypatch.setattr(
        router_service,
        "connect_router",
        lambda: api,
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="existing profiles are immutable",
    ):
        router_service.activate_hotspot_device(
            mac_address="AA:BB:CC:DD:EE:FF",
            download_speed_mbps=10,
            upload_speed_mbps=5,
            ip_address="10.20.0.254",
        )

    profiles = api.paths[("ip", "hotspot", "user", "profile")]
    assert profiles == [original_profile]
    assert api.active_devices == []
    assert api.closed is True


def test_activation_rejects_missing_device_queue(
    monkeypatch, router_settings
):
    api = FakeAPI(
        active_devices=[
            {
                "user": "AA:BB:CC:DD:EE:FF",
                "address": "10.20.0.254",
                "server": "WEZA-Hotspot-Server",
            }
        ],
        simple_queues=[],
    )


    api.paths[("ip", "hotspot", "user", "profile")].append({
        ".id": "*matching-profile",
        "name": "WEZA-2M-5M",
        "rate-limit": "2M/5M",
    })
    api.paths[("ip", "hotspot", "user")].append({
        ".id": "*matching-user",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "WEZA-2M-5M",
        "server": "WEZA-Hotspot-Server",
        "disabled": "no",
    })

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="per-device Hotspot speed queue",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    assert api.closed is True


def test_activation_accepts_routeros_numeric_queue_limit(
    monkeypatch, router_settings
):
    api = FakeAPI(
        active_devices=[
            {
                "user": "AA:BB:CC:DD:EE:FF",
                "address": "10.20.0.254",
                "server": "WEZA-Hotspot-Server",
            }
        ],
        simple_queues=[
            {
                "name": "<hotspot-AA:BB:CC:DD:EE:FF>",
                "target": "10.20.0.254/32",
                "max-limit": "2000000/5000000",
            }
        ],
    )


    api.paths[("ip", "hotspot", "user", "profile")].append({
        ".id": "*matching-profile",
        "name": "WEZA-2M-5M",
        "rate-limit": "2M/5M",
    })
    api.paths[("ip", "hotspot", "user")].append({
        ".id": "*matching-user",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "WEZA-2M-5M",
        "server": "WEZA-Hotspot-Server",
        "disabled": "no",
    })

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    result = router_service.activate_hotspot_device(
        "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
    )

    assert result["status"] == "ACTIVE"
    assert result["upload_speed_mbps"] == 2
    assert result["download_speed_mbps"] == 5
    assert api.closed is True


def test_activation_rejects_incorrect_device_queue_limit(
    monkeypatch, router_settings
):
    api = FakeAPI(
        active_devices=[
            {
                "user": "AA:BB:CC:DD:EE:FF",
                "address": "10.20.0.254",
                "server": "WEZA-Hotspot-Server",
            }
        ],
        simple_queues=[
            {
                "name": "<hotspot-AA:BB:CC:DD:EE:FF>",
                "target": "10.20.0.254/32",
                "max-limit": "1M/2M",
            }
        ],
    )


    api.paths[("ip", "hotspot", "user", "profile")].append({
        ".id": "*matching-profile",
        "name": "WEZA-2M-5M",
        "rate-limit": "2M/5M",
    })
    api.paths[("ip", "hotspot", "user")].append({
        ".id": "*matching-user",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "WEZA-2M-5M",
        "server": "WEZA-Hotspot-Server",
        "disabled": "no",
    })

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="does not enforce the purchased speed limit",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    assert api.closed is True


def test_activation_rejects_queue_with_wrong_name(
    monkeypatch, router_settings
):
    api = FakeAPI(
        active_devices=[
            {
                "user": "AA:BB:CC:DD:EE:FF",
                "address": "10.20.0.254",
                "server": "WEZA-Hotspot-Server",
            }
        ],
        simple_queues=[
            {
                "name": "unexpected-queue",
                "target": "10.20.0.254/32",
                "max-limit": "2M/5M",
            }
        ],
    )


    api.paths[("ip", "hotspot", "user", "profile")].append({
        ".id": "*matching-profile",
        "name": "WEZA-2M-5M",
        "rate-limit": "2M/5M",
    })
    api.paths[("ip", "hotspot", "user")].append({
        ".id": "*matching-user",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "WEZA-2M-5M",
        "server": "WEZA-Hotspot-Server",
        "disabled": "no",
    })

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="per-device Hotspot speed queue",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    assert api.closed is True


def test_failed_activation_removes_new_user_and_speed_profile(
    monkeypatch, router_settings
):
    api = FakeAPI()

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )
    monkeypatch.setattr(
        router_service, "_rate_limit_matches", lambda *args: False
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="does not enforce the purchased speed limit",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert users == []
    assert profiles == []
    assert api.active_devices == []
    assert api.closed is True


def test_failed_activation_restores_existing_user_and_speed_profile(
    monkeypatch, router_settings
):
    api = FakeAPI()

    original_profile = {
        ".id": "*profile-existing",
        "name": "WEZA-2M-5M",
        "rate-limit": "2M/5M",
    }
    original_user = {
        ".id": "*user-existing",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "old-profile",
        "server": "old-server",
        "disabled": "yes",
    }

    api.paths[("ip", "hotspot", "user", "profile")].append(
        dict(original_profile)
    )
    api.paths[("ip", "hotspot", "user")].append(
        dict(original_user)
    )

    fake_path_type = type(api.path("ip", "hotspot", "user"))
    real_update = fake_path_type.update

    def authenticate_with_bad_queue(self, **kwargs):
        real_update(self, **kwargs)

        if (
            self.records is api.paths[("ip", "hotspot", "user")]
            and kwargs.get("profile") == "WEZA-2M-5M"
        ):
            user = next(
                user for user in self.records
                if user.get(".id") == kwargs.get(".id")
            )
            api._simulate_authentication(user)
            api.simple_queues[0]["max-limit"] = "1M/1M"

    monkeypatch.setattr(
        fake_path_type, "update", authenticate_with_bad_queue
    )
    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="does not enforce the purchased speed limit",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert users == [original_user]
    assert profiles == [original_profile]
    assert api.closed is True


def test_activation_reports_rollback_failure_without_hiding_original_error(
    monkeypatch, router_settings
):
    api = FakeAPI()

    original_profile = {
        ".id": "*profile-existing",
        "name": "WEZA-2M-5M",
        "rate-limit": "2M/5M",
    }
    original_user = {
        ".id": "*user-existing",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "old-profile",
        "server": "old-server",
        "disabled": "yes",
    }

    api.paths[("ip", "hotspot", "user", "profile")].append(
        dict(original_profile)
    )
    api.paths[("ip", "hotspot", "user")].append(
        dict(original_user)
    )

    fake_path_type = type(api.path("ip", "hotspot", "user"))
    real_update = fake_path_type.update

    def fail_user_restore(self, **kwargs):
        if (
            self.records is api.paths[("ip", "hotspot", "user")]
            and kwargs.get("profile") == "old-profile"
        ):
            raise RuntimeError("simulated RouterOS user restore rejection")

        real_update(self, **kwargs)

        if (
            self.records is api.paths[("ip", "hotspot", "user")]
            and kwargs.get("profile") == "WEZA-2M-5M"
        ):
            user = next(
                user for user in self.records
                if user.get(".id") == kwargs.get(".id")
            )
            api._simulate_authentication(user)
            api.simple_queues[0]["max-limit"] = "1M/1M"

    monkeypatch.setattr(
        fake_path_type, "update", fail_user_restore
    )
    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError
    ) as exc_info:
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    message = str(exc_info.value)
    assert "does not enforce the purchased speed limit" in message
    assert "Rollback also failed" in message
    assert "Hotspot user rollback failed" in message
    assert "simulated RouterOS user restore rejection" in message

    users = api.paths[("ip", "hotspot", "user")]
    assert users[0]["profile"] == "WEZA-2M-5M"
    assert users[0]["server"] == "WEZA-Hotspot-Server"
    assert users[0]["disabled"] == "no"

    profiles = api.paths[("ip", "hotspot", "user", "profile")]
    assert profiles == [original_profile]
    assert api.closed is True


def test_rollback_preserves_new_profile_when_session_removal_fails(
    monkeypatch, router_settings
):
    class MismatchedQueueFakeAPI(FakeAPI):
        def _complete_authentication(self, hotspot_user):
            super()._complete_authentication(hotspot_user)
            self.simple_queues[-1]["max-limit"] = "1M/1M"

    api = MismatchedQueueFakeAPI()

    real_remove = FakePath.remove

    def fail_active_session_removal(self, *record_ids):
        if self.records is api.active_devices:
            raise RuntimeError("simulated active-session removal failure")
        return real_remove(self, *record_ids)

    monkeypatch.setattr(
        FakePath, "remove", fail_active_session_removal
    )
    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError
    ) as exc_info:
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    assert "Rollback also failed" in str(exc_info.value)
    assert "New Hotspot session rollback failed" in str(exc_info.value)

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    # Preserve the user while RouterOS may still have an active session.
    assert len(users) == 1
    assert users[0]["name"] == "AA:BB:CC:DD:EE:FF"
    assert users[0]["profile"] == "WEZA-2M-5M"
    assert len(api.active_devices) == 1
    assert profiles == [
        {
            ".id": "*1",
            "name": "WEZA-2M-5M",
            "rate-limit": "2M/5M",
        }
    ]
    assert api.closed is True


def test_failed_activation_removes_all_newly_created_sessions(
    monkeypatch, router_settings
):
    class MultipleSessionFakeAPI(FakeAPI):
        def _complete_authentication(self, hotspot_user):
            super()._complete_authentication(hotspot_user)

            self.active_devices.append({
                ".id": "*active-extra",
                "user": hotspot_user["name"],
                "address": "10.20.0.253",
                "server": hotspot_user["server"],
            })

    api = MultipleSessionFakeAPI()

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(router_service.RouterActivationError):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    assert api.active_devices == []
    assert api.paths[("ip", "hotspot", "user")] == []
    assert api.paths[("ip", "hotspot", "user", "profile")] == []
    assert api.closed is True

def test_missing_new_session_id_preserves_user_and_profile(
    monkeypatch, router_settings
):
    class MissingSessionIdFakeAPI(FakeAPI):
        def _complete_authentication(self, hotspot_user):
            super()._complete_authentication(hotspot_user)
            self.active_devices[-1].pop(".id", None)

    api = MissingSessionIdFakeAPI()
    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError
    ) as exc_info:
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    message = str(exc_info.value)
    assert "Authenticated Hotspot session has no RouterOS ID" in message
    assert "Rollback also failed" in message
    assert "could not be safely removed" in message

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert len(api.active_devices) == 1
    assert ".id" not in api.active_devices[0]
    assert len(users) == 1
    assert users[0]["name"] == "AA:BB:CC:DD:EE:FF"
    assert users[0]["profile"] == "WEZA-2M-5M"
    assert len(profiles) == 1
    assert profiles[0]["name"] == "WEZA-2M-5M"
    assert api.closed is True


def test_rollback_preserves_user_when_session_removal_silently_fails(
    monkeypatch, router_settings
):
    class MismatchedQueueFakeAPI(FakeAPI):
        def _complete_authentication(self, hotspot_user):
            super()._complete_authentication(hotspot_user)
            self.simple_queues[-1]["max-limit"] = "1M/1M"

    api = MismatchedQueueFakeAPI()
    real_remove = FakePath.remove

    def silently_fail_active_session_removal(self, *record_ids):
        if self.records is api.active_devices:
            return None
        return real_remove(self, *record_ids)

    monkeypatch.setattr(
        FakePath, "remove", silently_fail_active_session_removal
    )
    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError
    ) as exc_info:
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    message = str(exc_info.value)
    assert "Rollback also failed" in message
    assert "still exist after rollback removal" in message
    assert "Hotspot user configuration was preserved" in message

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert len(api.active_devices) == 1
    assert len(users) == 1
    assert users[0]["name"] == "AA:BB:CC:DD:EE:FF"
    assert users[0]["profile"] == "WEZA-2M-5M"
    assert len(profiles) == 1
    assert profiles[0]["name"] == "WEZA-2M-5M"
    assert api.closed is True


def test_rollback_preserves_user_when_replacement_session_has_new_id(
    monkeypatch, router_settings
):
    class MismatchedQueueFakeAPI(FakeAPI):
        def _complete_authentication(self, hotspot_user):
            super()._complete_authentication(hotspot_user)
            self.simple_queues[-1]["max-limit"] = "1M/1M"

    api = MismatchedQueueFakeAPI()
    real_remove = FakePath.remove

    def replace_session_after_removal(self, *record_ids):
        if self.records is api.active_devices:
            removed_sessions = [
                record.copy()
                for record in self.records
                if record.get(".id") in record_ids
            ]
            result = real_remove(self, *record_ids)

            for removed_session in removed_sessions:
                api.active_devices.append({
                    ".id": "*replacement-session",
                    "user": removed_session["user"],
                    "address": removed_session["address"],
                    "server": removed_session["server"],
                })

            return result

        return real_remove(self, *record_ids)

    monkeypatch.setattr(
        FakePath, "remove", replace_session_after_removal
    )
    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError
    ) as exc_info:
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    message = str(exc_info.value)
    assert "Rollback also failed" in message
    assert "matching Hotspot session remains active" in message
    assert "Hotspot user configuration was preserved" in message

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert len(api.active_devices) == 1
    assert api.active_devices[0][".id"] == "*replacement-session"
    assert len(users) == 1
    assert users[0]["name"] == "AA:BB:CC:DD:EE:FF"
    assert users[0]["profile"] == "WEZA-2M-5M"
    assert len(profiles) == 1
    assert profiles[0]["name"] == "WEZA-2M-5M"
    assert api.closed is True



def test_empty_profile_add_id_preserves_unidentified_profile(
    monkeypatch, router_settings
):
    api = FakeAPI(empty_profile_add_id=True)

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="Could not identify the newly created speed profile",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    profiles = api.paths[("ip", "hotspot", "user", "profile")]
    users = api.paths[("ip", "hotspot", "user")]

    assert len(profiles) == 1
    assert profiles[0]["name"] == "WEZA-2M-5M"
    assert users == []
    assert api.closed is True


def test_empty_user_add_id_preserves_unidentified_user_and_profile(
    monkeypatch, router_settings
):
    api = FakeAPI(empty_user_add_id=True)

    monkeypatch.setattr(
        router_service, "connect_router", lambda: api
    )

    with pytest.raises(
        router_service.RouterActivationError,
        match="Could not identify the newly created Hotspot user",
    ):
        router_service.activate_hotspot_device(
            "AA:BB:CC:DD:EE:FF", 5, 2, "10.20.0.254"
        )

    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]

    assert len(users) == 1
    assert users[0]["name"] == "AA:BB:CC:DD:EE:FF"
    assert len(profiles) == 1
    assert profiles[0]["name"] == "WEZA-2M-5M"
    # User creation may already have triggered authentication.
    # Preserve the resulting session because its ID was not tracked.
    assert len(api.active_devices) == 1
    assert api.active_devices[0]["user"] == "AA:BB:CC:DD:EE:FF"
    assert api.closed is True


def test_reconciliation_reads_only_and_verifies_late_speed_queue(
    monkeypatch, router_settings
):
    mac = "AA:BB:CC:DD:EE:FF"
    api = FakeAPI(active_devices=[])
    monkeypatch.setattr(router_service, "connect_router", lambda: api)

    with pytest.raises(router_service.RouterActivationUnconfirmed):
        router_service.activate_hotspot_device(mac, 5, 2, verify_only=True)
    users = api.paths[("ip", "hotspot", "user")]
    profiles = api.paths[("ip", "hotspot", "user", "profile")]
    assert users == []
    assert profiles == []

    profiles.append({"name": "WEZA-2M-5M", "rate-limit": "2M/5M"})
    user = {
        "name": mac,
        "profile": "WEZA-2M-5M",
        "server": "WEZA-Hotspot-Server",
    }
    users.append(user)
    api._complete_authentication(user)
    api.simple_queues[0]["max-limit"] = "1M/5M"
    with pytest.raises(router_service.RouterActivationError, match="speed limit"):
        router_service.activate_hotspot_device(mac, 5, 2, verify_only=True)

    api.simple_queues[0]["max-limit"] = "2M/5M"
    result = router_service.activate_hotspot_device(mac, 5, 2, verify_only=True)
    assert result["status"] == "ACTIVE"
    assert users == [user]
    assert len(api.active_devices) == 1


def test_expiry_removes_reconnected_device_and_preserves_other_devices(monkeypatch):
    mac = "AA:BB:CC:DD:EE:FF"
    server = "WEZA-Hotspot-Server"
    api = FakeAPI(active_devices=[
        {".id": "*reconnected", "user": mac, "mac-address": mac, "server": server},
        {".id": "*other", "user": "another-user", "server": server},
    ])
    def verify_disabled_before_disconnect(_):
        assert user["disabled"] == "yes"

    api.initial_active_session_ids.clear()
    original_path = api.path

    def path(*segments):
        result = original_path(*segments)
        if segments == ("ip", "hotspot", "active"):
            result.on_remove = verify_disabled_before_disconnect
        return result

    api.path = path
    user = {".id": "*user", "name": mac, "server": server, "comment": "WEZA grant original", "disabled": "no"}
    api.paths[("ip", "hotspot", "user")].append(user)
    monkeypatch.setattr(router_service, "connect_router", lambda: api)
    monkeypatch.setattr(router_service, "router_settings", lambda: {"expected_identity": "CHR"})

    router_service.expire_hotspot_grant(mac, "original")
    router_service.expire_hotspot_grant(mac, "original")

    assert user["disabled"] == "yes"
    assert [entry[".id"] for entry in api.active_devices] == ["*other"]

    # An older expiry must never revoke a replacement grant.
    user.update({"comment": "WEZA grant later", "disabled": "no"})
    api.active_devices.append({".id": "*new", "user": mac, "mac-address": mac, "server": server})
    router_service.expire_hotspot_grant(mac, "original")
    assert user["disabled"] == "no"
    assert [entry[".id"] for entry in api.active_devices] == ["*other", "*new"]
