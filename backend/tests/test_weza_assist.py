from app.api.routes import assist


def test_assist_greets_and_acknowledges_without_referral(client, monkeypatch):
    def unexpected_model_call(*_):
        raise AssertionError("Basic conversation should not require the model")

    monkeypatch.setattr(assist, "ask_ollama", unexpected_model_call)
    for text, prefix in (("Hello! 👋", "Hi!"), ("Mambo", "Hi!"), ("Thank you.", "You’re welcome!")):
        message = [{"role": "user", "text": text}]
        body = client.post("/api/support/assist", json={"messages": message}).json()
        assert body["answer"].startswith(prefix)
        assert body["handoff"] is False
        assert body["sources"] == []


def test_assist_reads_current_faqs_and_accepts_only_supplied_sources(client, monkeypatch):
    monkeypatch.setenv("WEZA_ASSIST_MODEL", "fixture-model")
    monkeypatch.delenv("WEZA_ASSIST_RESOURCES", raising=False)

    def model(model_name, messages, sources):
        assert model_name == "fixture-model"
        assert messages[-1].text == "I paid but my internet is offline"
        faq = next(source for source in sources if "no internet" in source.title)
        return {"answer": "Reconnect to Weza Wi-Fi and check the connection status.", "source_ids": [faq.id, "invented"]}

    monkeypatch.setattr(assist, "ask_ollama", model)
    response = client.post("/api/support/assist", json={"messages": [
        {"role": "user", "text": "I paid but my internet is offline"},
    ]})
    assert response.status_code == 200
    result = response.json()
    assert not result["handoff"]
    assert result["sources"] == [{"title": "Payment received but no internet?", "url": "/support"}]


def test_assist_hands_off_unsupported_answers(client, monkeypatch):
    monkeypatch.setenv("WEZA_ASSIST_MODEL", "fixture-model")
    monkeypatch.setattr(assist, "ask_ollama", lambda *_: {"answer": "Something", "source_ids": ["made-up"]})
    result = client.post("/api/support/assist", json={"messages": [{"role": "user", "text": "Has my package expired?"}]}).json()
    assert result == {"answer": assist.FALLBACK, "sources": [], "handoff": True}


def test_assist_hands_off_when_the_latest_question_changes_topic(client, monkeypatch):
    monkeypatch.setenv("WEZA_ASSIST_MODEL", "fixture-model")
    monkeypatch.delenv("WEZA_ASSIST_RESOURCES", raising=False)

    def unexpected_model_call(*_):
        raise AssertionError("An unrelated question should not borrow sources from earlier turns")

    monkeypatch.setattr(assist, "ask_ollama", unexpected_model_call)
    for earlier, reply in (
        ("Hello", "Hi! Ask me about Weza packages, M-Pesa payments, or getting online."),
        ("I paid but my internet is offline", "Check your connection status."),
    ):
        result = client.post("/api/support/assist", json={"messages": [
            {"role": "user", "text": earlier},
            {"role": "assistant", "text": reply},
            {"role": "user", "text": "Could you help me with medieval pottery?"},
        ]}).json()
        assert result == {"answer": assist.FALLBACK, "sources": [], "handoff": True}


def test_assist_keeps_payment_context_for_a_follow_up(client, monkeypatch):
    monkeypatch.setenv("WEZA_ASSIST_MODEL", "fixture-model")
    monkeypatch.delenv("WEZA_ASSIST_RESOURCES", raising=False)

    def model(_, messages, sources):
        assert messages[-1].text == "Should I pay again?"
        faq = next(source for source in sources if source.title == "Payment received but no internet?")
        return {"answer": "Check your connection status before trying another payment.", "source_ids": [faq.id]}

    monkeypatch.setattr(assist, "ask_ollama", model)
    result = client.post("/api/support/assist", json={"messages": [
        {"role": "user", "text": "I paid but my internet is offline"},
        {"role": "assistant", "text": "Check your connection status."},
        {"role": "user", "text": "Should I pay again?"},
    ]}).json()
    assert not result["handoff"]
    assert result["sources"] == [{"title": "Payment received but no internet?", "url": "/support"}]


def test_public_sources_must_use_exact_approved_https_hosts(monkeypatch):
    monkeypatch.setenv("WEZA_ASSIST_RESOURCES", """[
        {"title": "Bad", "url": "https://www.safaricom.co.ke.evil.test/path"},
        {"title": "Approved help topic", "url": "https://wezawifi.co.ke/contact", "text": "Guidance"}
    ]""")
    assert [source.title for source in assist.published_resources()] == ["Approved help topic"]
    redacted = assist.sanitise("Email me at customer@example.test. My phone is +254 712 345 678 and my PIN is 1234.")
    assert "example.test" not in redacted and "254" not in redacted and "1234" not in redacted
