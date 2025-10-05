import pandas as pd

from src.data_loader import _coerce_types, _drop_duplicates, _contacts_to_customers


def test_coerce_types_datetime_numeric():
    df = pd.DataFrame({"d": ["2020-01-01", "bad"], "n": ["1", "x"]})
    out = _coerce_types(df, ["d"], ["n"])
    assert pd.api.types.is_datetime64_any_dtype(out["d"])  # type: ignore[index]
    assert pd.api.types.is_numeric_dtype(out["n"])  # type: ignore[index]
    assert pd.isna(out.loc[1, "d"])  # type: ignore[index]
    assert pd.isna(out.loc[1, "n"])  # type: ignore[index]


def test_drop_duplicates_subset():
    df = pd.DataFrame({"id": [1, 1, 2], "v": ["a", "a", "b"]})
    out, removed = _drop_duplicates(df, ["id"])
    assert len(out) == 2
    assert removed == 1


def test_contacts_to_customers_mapping():
    df = pd.DataFrame({
        "ID": ["1", "1"],
        "Company": ["Company A", "Company A"],
        "Last Name": ["Doe", "Doe"],
        "First Name": ["John", "John"],
        "Job Title": ["Owner", "Owner"],
        "Business Phone": ["123", "123"],
        "Fax Number": ["456", "456"],
        "Address": ["Street 1", "Street 1"],
        "City": ["City", "City"],
        "State/Province": ["ST", "ST"],
        "ZIP/Postal Code": ["00000", "00000"],
        "Country/Region": ["US", "US"],
    })
    mapped = _contacts_to_customers(df)
    assert not mapped.empty
    assert set(["customer_id", "company_name", "contact_name"]).issubset(set(mapped.columns))
    # deduped
    assert len(mapped) == 1

