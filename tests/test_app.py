import pytest

from app import create_app, results_as_text


@pytest.fixture
def client():
    return create_app().test_client()


@pytest.fixture
def store():
    return create_app().config["DRUG_STORE"]


def test_find_prefers_exact_brand_then_generic_then_substring(store):
    assert store.find("lexapro").name == "Lexapro"
    assert store.find("  ESCITALOPRAM ").name == "Lexapro"
    assert store.find("xycodon") is not None
    assert store.find("definitely-not-a-drug") is None
    assert store.find("   ") is None


def test_index_lists_database_when_no_search(client):
    html = client.get("/").get_data(as_text=True)
    assert "Drugs in database" in html
    assert 'data-name="Lexapro"' in html
    assert "Results" not in html


def test_index_renders_results_from_query_string(client):
    html = client.get("/?drug=Lexapro&drug=notarealdrug&drug=").get_data(as_text=True)
    assert "1 found in database" in html
    assert "1 linked to Drugs.com" in html
    assert "Oral Side Effects" in html
    assert "Xerostomia" in html
    assert "wasn't found in the local database" in html
    # Inputs are refilled with what was searched (blank dropped).
    assert html.count('name="drug"') == 2 + 1  # 2 rows + the <template> row


def test_index_escapes_user_input(client):
    html = client.get("/?drug=<script>alert(1)</script>").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html


def test_index_caps_number_of_drugs(client):
    qs = "&".join(f"drug=x{i}" for i in range(30))
    html = client.get(f"/?{qs}").get_data(as_text=True)
    assert "20 linked to Drugs.com" in html


def test_copy_text_format(store):
    text = results_as_text([("lexapro", store.find("lexapro")), ("nope", None)])
    assert text.startswith("Escitalopram\n  Class: SSRI\n  Side Effects:\n    • Xerostomia")
    assert text.endswith("nope\n  Not found in database.")


def test_api_search(client):
    r = client.post("/api/drugs/search", json={"names": ["Lexapro", "zzz"]})
    assert r.status_code == 200
    first, second = r.get_json()["results"]
    assert first["genericName"] == "Escitalopram"
    assert first["sideEffects"][0] == {"effect": "Xerostomia", "prevalence": "COMMON"}
    assert second is None


@pytest.mark.parametrize("body", [{}, {"names": []}, {"names": [""]}, {"names": ["a"] * 21}, {"names": [1]}])
def test_api_search_validation(client, body):
    assert client.post("/api/drugs/search", json=body).status_code == 400


def test_api_lists_and_autocomplete(client):
    assert len(client.get("/api/drugs").get_json()["drugs"]) > 100
    names = client.get("/api/drugs/names").get_json()["drugs"]
    assert {"name", "genericName", "commonUse"} == set(names[0])
    assert client.get("/api/drugs/autocomplete?q=l").get_json() == {"suggestions": []}
    sugg = client.get("/api/drugs/autocomplete?q=lex").get_json()["suggestions"]
    assert {"name": "Lexapro", "genericName": "Escitalopram"} in sugg
    assert len(client.get("/api/drugs/autocomplete?q=in").get_json()["suggestions"]) <= 8


def test_changelog_and_404(client):
    assert b"Ver. 0.6.12" in client.get("/changelog").data
    assert client.get("/nope").status_code == 404
