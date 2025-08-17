from cake_dictionary import resolve_country_iso3_from_user_input, currency_to_iso3

def test_tenge_maps_to_kaz():
    assert resolve_country_iso3_from_user_input("тенге") == "KAZ"

def test_usd_maps_to_usa():
    assert currency_to_iso3("USD") == "USA"