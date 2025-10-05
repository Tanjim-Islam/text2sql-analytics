from __future__ import annotations

import os
from datetime import date

import pandas as pd

from text2sql_analytics.data_loader import DataLoader, LoaderConfig
from text2sql_analytics.database import Database
from text2sql_analytics.query_validator import sanitize_and_validate


def test_database_select_one():
    db = Database.from_env()
    assert db.select_one() == 1


def test_query_validator_enforces_limit():
    out = sanitize_and_validate("select * from customers limit 50000", row_limit=1000)
    assert "LIMIT 1000" in out.upper()


def test_data_loader_pipeline_with_excel(tmp_path):
    excel_path = tmp_path / "northwind.xlsx"
    with pd.ExcelWriter(excel_path) as writer:
        pd.DataFrame([{"CustomerID": "ALFKI", "CompanyName": "Alfreds"}]).to_excel(
            writer, sheet_name="Customers", index=False
        )
        pd.DataFrame(
            [
                {
                    "EmployeeID": 1,
                    "LastName": "Doe",
                    "FirstName": "Jane",
                    "Title": "Sales Representative",
                    "TitleOfCourtesy": "Ms.",
                    "BirthDate": pd.NaT,
                    "HireDate": date(2020, 1, 1),
                    "Address": "1 Main St",
                    "City": "Seattle",
                    "Region": "WA",
                    "PostalCode": "98101",
                    "Country": "USA",
                    "HomePhone": "",
                    "Extension": "",
                    "Notes": "",
                    "ReportsTo": None,
                }
            ]
        ).to_excel(writer, sheet_name="Employees", index=False)
        pd.DataFrame(
            [
                {
                    "OrderID": 10248,
                    "CustomerID": "ALFKI",
                    "EmployeeID": 1,
                    "OrderDate": date(2021, 1, 10),
                    "RequiredDate": date(2021, 1, 17),
                    "ShippedDate": date(2021, 1, 12),
                    "ShipVia": 1,
                    "Freight": 32.38,
                    "ShipName": "Alfreds",
                    "ShipAddress": "1 Main St",
                    "ShipCity": "Seattle",
                    "ShipRegion": "WA",
                    "ShipPostalCode": "98101",
                    "ShipCountry": "USA",
                }
            ]
        ).to_excel(writer, sheet_name="Orders", index=False)
        pd.DataFrame(
            [
                {"CategoryID": 1, "CategoryName": "Beverages", "Description": "Drinks"},
            ]
        ).to_excel(writer, sheet_name="Categories", index=False)
        pd.DataFrame(
            [
                {
                    "ProductID": 1,
                    "ProductName": "Chai",
                    "SupplierID": 1,
                    "CategoryID": 1,
                    "QuantityPerUnit": "10 boxes x 20 bags",
                    "UnitPrice": 18.0,
                    "UnitsInStock": 39,
                    "UnitsOnOrder": 0,
                    "ReorderLevel": 10,
                    "Discontinued": 0,
                },
            ]
        ).to_excel(writer, sheet_name="Products", index=False)
        pd.DataFrame(
            [
                {
                    "OrderID": 10248,
                    "ProductID": 1,
                    "UnitPrice": 18.0,
                    "Quantity": 10,
                    "Discount": 0.0,
                }
            ]
        ).to_excel(writer, sheet_name="Order Details", index=False)
    os.environ.setdefault("DB_USER_ADMIN", "admin")
    os.environ.setdefault("DB_PASS_ADMIN", "changeme")

    cfg = LoaderConfig(
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5433")),
        db_name=os.getenv("DB_NAME", "northwind"),
        db_user=os.getenv("DB_USER_ADMIN", "admin"),
        db_pass=os.getenv("DB_PASS_ADMIN", "changeme"),
        excel_path=str(excel_path),
    )
    loader = DataLoader(cfg)
    loader.create_normalized_schema()
    counts = loader.load_from_excel()
    assert counts.get("customers", 0) >= 1
    assert counts.get("orders", 0) >= 1
    assert counts.get("order_details", 0) >= 1

    report = loader.generate_report()
    assert "row_counts" in report and isinstance(report["row_counts"], dict)

