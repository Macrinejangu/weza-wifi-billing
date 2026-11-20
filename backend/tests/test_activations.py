
import pytest

import app.services.router as router_service


class FakePath:
    def __init__(self, records, on_add=None, on_read=None):
        self.records = records
        self.on_add = on_add
        self.on_read = on_read

    def __iter__(self):
        if self.on_read:
            self.on_read()
        return iter(self.records)

    def add(self, **kwargs):
        record = {**kwargs, ".id": f"*{len(self.records) + 1}"}
        self.records.append(record)

        if self.on_add:
            self.on_add(record)

        return record[".id"]

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
    ):
        self.closed = False
        self.auto_authenticate = active_devices is None
        self.authentication_delay_polls = authentication_delay_polls
        self.active_poll_count = 0
        self.pending_hotspot_user = None

        self.active_devices = (
            [] if active_devices is None else active_devices
        )

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

        if parts == ("ip", "hotspot", "user"):
            return FakePath(records, on_add=self._simulate_authentication)

        if parts == ("ip", "hotspot", "active"):
            return FakePath(records, on_read=self._poll_authentication)

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


def test_existing_hotspot_user_is_updated_without_duplicates(
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
                "max-limit": "5M/10M",
            }
        ],
    )

    api.paths[("ip", "hotspot", "user")].append({
        ".id": "*existing",
        "name": "AA:BB:CC:DD:EE:FF",
        "profile": "default",
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

    assert len(users) == 1
    assert users[0]["profile"] == "WEZA-5M-10M"
    assert result["status"] == "ACTIVE"
    assert result["rate_limit"] == "5M/10M"



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


def test_existing_speed_profile_with_wrong_rate_is_corrected(
    monkeypatch, router_settings
):
    api = FakeAPI()

    api.paths[("ip", "hotspot", "user", "profile")].append({
        ".id": "*existing",
        "name": "WEZA-5M-10M",
        "rate-limit": "2M/5M",
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
    assert profiles[0]["rate-limit"] == "5M/10M"
    assert result["rate_limit"] == "5M/10M"


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
