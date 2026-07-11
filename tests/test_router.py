from app.core.router import SMS, WHATSAPP, choose_channel, route


def test_us_gets_sms():
    assert choose_channel("US") == SMS


def test_canada_gets_whatsapp_not_sms():
    # +1 is shared with the US, but CA must route to WhatsApp based on stored country.
    assert choose_channel("CA") == WHATSAPP


def test_intl_gets_whatsapp():
    for c in ("GB", "IN", "DE", "BR", "JP"):
        assert choose_channel(c) == WHATSAPP


def test_route_skips_when_not_opted_in():
    us_no_optin = {"country": "US", "active": 1, "sms_opt_in": 0, "whatsapp_opt_in": 0}
    d = route(us_no_optin)
    assert d.send is False and d.channel == SMS and "opt-in" in d.reason


def test_route_sends_when_opted_in():
    intl = {"country": "IN", "active": 1, "sms_opt_in": 0, "whatsapp_opt_in": 1}
    d = route(intl)
    assert d.send is True and d.channel == WHATSAPP


def test_route_skips_inactive():
    d = route({"country": "US", "active": 0, "sms_opt_in": 1})
    assert d.send is False and "inactive" in d.reason
