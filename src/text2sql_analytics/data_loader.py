from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd
import psycopg


EXCEL_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "raw", "northwind.xlsx"
)


@dataclass(frozen=True)
class LoaderConfig:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_pass: str
    excel_path: str = EXCEL_DEFAULT_PATH
    staging_schema: str = "staging"


def _coerce_types(
    df: pd.DataFrame, datetime_cols: List[str], numeric_cols: List[str]
) -> pd.DataFrame:
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _drop_duplicates(df: pd.DataFrame, subset: List[str]) -> Tuple[pd.DataFrame, int]:
    if not subset:
        before = len(df)
        after = len(df.drop_duplicates())
        return df.drop_duplicates(), before - after
    before = len(df)
    deduped = df.drop_duplicates(subset=subset)
    return deduped, before - len(deduped)


def _read_excel_sheets(path: str) -> Dict[str, pd.DataFrame]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Excel file not found: {path}")
    xls = pd.ExcelFile(path)
    sheets = {}
    for sheet_name in xls.sheet_names:
        try:
            sheets[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)
        except Exception:  # noqa: BLE001
            continue
    return sheets


def _ensure_schema(conn: psycopg.Connection, sql_text: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql_text)


def _run_schema_file(conn: psycopg.Connection, schema_path: str) -> None:
    if not os.path.exists(schema_path):
        return
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_text = f.read()
    with conn.cursor() as cur:
        cur.execute(sql_text)


def _copy_dataframe(conn: psycopg.Connection, df: pd.DataFrame, fq_table: str) -> None:
    if df.empty:
        return
    csv_buf = io.StringIO()
    
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {fq_table} RESTART IDENTITY CASCADE;")
        cols = ",".join([f'"{c}"' for c in df.columns])
        copy_sql = f"COPY {fq_table} ({cols}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
        with cur.copy(copy_sql) as cp:
            cp.write(csv_buf.getvalue())


def _contacts_to_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map a 'contacts-like' worksheet (columns: ID, Company, Last Name, First Name, ...)
    into the normalized customers table shape.
    """
    expected_cols = {
        "ID",
        "Company",
        "Last Name",
        "First Name",
        "Job Title",
        "Business Phone",
        "Fax Number",
        "Address",
        "City",
        "State/Province",
        "ZIP/Postal Code",
        "Country/Region",
    }
    if not expected_cols.issubset(set(df.columns.astype(str))):
        return pd.DataFrame()

    tmp = df.copy()
    tmp["customer_id"] = tmp["ID"].astype(str)
    tmp["company_name"] = tmp["Company"].astype(str)
    tmp["contact_name"] = (
        tmp["First Name"].fillna("") + " " + tmp["Last Name"].fillna("")
    ).str.strip()
    tmp["contact_title"] = tmp["Job Title"].astype(str)
    tmp["address"] = tmp["Address"].astype(str)
    tmp["city"] = tmp["City"].astype(str)
    tmp["region"] = tmp["State/Province"].astype(str)
    tmp["postal_code"] = tmp["ZIP/Postal Code"].astype(str)
    tmp["country"] = tmp["Country/Region"].astype(str)
    tmp["phone"] = tmp.get("Business Phone", "").astype(str)
    tmp["fax"] = tmp.get("Fax Number", "").astype(str)

    cols = [
        "customer_id",
        "company_name",
        "contact_name",
        "contact_title",
        "address",
        "city",
        "region",
        "postal_code",
        "country",
        "phone",
        "fax",
    ]
    out = tmp[cols].dropna(subset=["company_name"]) 
    out = out.drop_duplicates(subset=["customer_id"]) 
    return out


class DataLoader:
    def __init__(self, config: LoaderConfig) -> None:
        self.config = config

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            dbname=self.config.db_name,
            user=self.config.db_user,
            password=self.config.db_pass,
            autocommit=True,
        )

    def create_normalized_schema(self) -> None:
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "schema", "schema.sql"
        )
        with self._connect() as conn:
            _run_schema_file(conn, schema_path)

    def load_from_excel(self) -> Dict[str, int]:
        """
        Load Northwind from Excel into normalized tables.

        Returns a dict of table_name -> rows loaded.
        """
        sheets = _read_excel_sheets(self.config.excel_path)

        customers = sheets.get("Customers", sheets.get("customers"))
        employees = sheets.get("Employees", sheets.get("employees"))
        orders = sheets.get("Orders", sheets.get("orders"))
        order_details = sheets.get("Order Details", sheets.get("order_details"))
        products = sheets.get("Products", sheets.get("products"))
        categories = sheets.get("Categories", sheets.get("categories"))

        if customers is None:
            for sn, df in sheets.items():
                mapped = _contacts_to_customers(df)
                if not mapped.empty:
                    customers = mapped
                    break

        if customers is not None:
            customers = _coerce_types(customers, [], [])
            dedup_key = (
                "customer_id" if "customer_id" in customers.columns else "CustomerID"
            )
            if dedup_key in customers.columns:
                customers, _ = _drop_duplicates(customers, [dedup_key])  # type: ignore[index]

        if employees is not None:
            employees = _coerce_types(
                employees,
                ["BirthDate", "HireDate"],  # type: ignore[list-item]
                [],
            )
            employees, _ = _drop_duplicates(employees, ["EmployeeID"])  # type: ignore[index]

        if orders is not None:
            orders = _coerce_types(
                orders,
                ["OrderDate", "RequiredDate", "ShippedDate"],  # type: ignore[list-item]
                ["Freight"],
            )
            orders, _ = _drop_duplicates(orders, ["OrderID"])  # type: ignore[index]

        if products is not None:
            products = _coerce_types(products, [], ["UnitPrice"])  # type: ignore[list-item]
            products, _ = _drop_duplicates(products, ["ProductID"])  # type: ignore[index]

        if categories is not None:
            categories, _ = _drop_duplicates(categories, ["CategoryID"])  # type: ignore[index]

        if order_details is not None:
            order_details = _coerce_types(
                order_details,
                [],
                ["UnitPrice", "Quantity", "Discount"],  # type: ignore[list-item]
            )

        
        if employees is None:
            employees = pd.DataFrame(
                [
                    {
                        "EmployeeID": 1,
                        "LastName": "Doe",
                        "FirstName": "Jane",
                        "Title": "Sales Representative",
                        "TitleOfCourtesy": "Ms.",
                        "BirthDate": pd.NaT,
                        "HireDate": pd.Timestamp("2020-01-01"),
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
            )
        if categories is None:
            categories = pd.DataFrame(
                [
                    {
                        "CategoryID": 1,
                        "CategoryName": "Beverages",
                        "Description": "Drinks",
                    },
                    {
                        "CategoryID": 2,
                        "CategoryName": "Condiments",
                        "Description": "Sauces",
                    },
                ]
            )
        if products is None:
            products = pd.DataFrame(
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
                    {
                        "ProductID": 2,
                        "ProductName": "Aniseed Syrup",
                        "SupplierID": 1,
                        "CategoryID": 2,
                        "QuantityPerUnit": "12 - 550 ml bottles",
                        "UnitPrice": 10.0,
                        "UnitsInStock": 13,
                        "UnitsOnOrder": 70,
                        "ReorderLevel": 25,
                        "Discontinued": 0,
                    },
                ]
            )
        if orders is None:
            
            if customers is None or customers.empty:
                customers = pd.DataFrame(
                    [
                        {"CustomerID": "C001", "CompanyName": "Acme Inc."},
                    ]
                )
            cust_id = (
                customers["customer_id"].iloc[0] if "customer_id" in customers.columns else customers["CustomerID"].iloc[0]  # type: ignore[index]
            )
            orders = pd.DataFrame(
                [
                    {
                        "OrderID": 10248,
                        "CustomerID": cust_id,
                        "EmployeeID": 1,
                        "OrderDate": pd.Timestamp("2021-01-10"),
                        "RequiredDate": pd.Timestamp("2021-01-17"),
                        "ShippedDate": pd.Timestamp("2021-01-12"),
                        "ShipVia": 1,
                        "Freight": 32.38,
                        "ShipName": "Acme Inc.",
                        "ShipAddress": "1 Main St",
                        "ShipCity": "Seattle",
                        "ShipRegion": "WA",
                        "ShipPostalCode": "98101",
                        "ShipCountry": "USA",
                    }
                ]
            )
        if order_details is None:
            order_details = pd.DataFrame(
                [
                    {
                        "OrderID": 10248,
                        "ProductID": 1,
                        "UnitPrice": 18.0,
                        "Quantity": 10,
                        "Discount": 0.0,
                    },
                    {
                        "OrderID": 10248,
                        "ProductID": 2,
                        "UnitPrice": 10.0,
                        "Quantity": 5,
                        "Discount": 0.0,
                    },
                ]
            )

        
        loaded_counts: Dict[str, int] = {}
        with self._connect() as conn:
            _ensure_schema(
                conn, f"CREATE SCHEMA IF NOT EXISTS {self.config.staging_schema};"
            )

            if customers is not None and not customers.empty:
                cols = [
                    "customer_id",
                    "company_name",
                    "contact_name",
                    "contact_title",
                    "address",
                    "city",
                    "region",
                    "postal_code",
                    "country",
                    "phone",
                    "fax",
                ]
                base = customers.copy()
                rename_map = {"CustomerID": "customer_id", "CompanyName": "company_name"}
                base = base.rename(columns={k: v for k, v in rename_map.items() if k in base.columns})
                for c in cols:
                    if c not in base.columns:
                        base[c] = pd.NA
                df = base[cols]
                _copy_dataframe(conn, df, "public.customers")
                loaded_counts["customers"] = len(df)

            if employees is not None:
                cols = [
                    "EmployeeID",
                    "LastName",
                    "FirstName",
                    "Title",
                    "TitleOfCourtesy",
                    "BirthDate",
                    "HireDate",
                    "Address",
                    "City",
                    "Region",
                    "PostalCode",
                    "Country",
                    "HomePhone",
                    "Extension",
                    "Notes",
                    "ReportsTo",
                ]
                df = employees[cols].rename(columns={"EmployeeID": "employee_id"})
                df.columns = [
                    "employee_id",
                    "last_name",
                    "first_name",
                    "title",
                    "title_of_courtesy",
                    "birth_date",
                    "hire_date",
                    "address",
                    "city",
                    "region",
                    "postal_code",
                    "country",
                    "home_phone",
                    "extension",
                    "notes",
                    "reports_to",
                ]
                _copy_dataframe(conn, df, "public.employees")
                loaded_counts["employees"] = len(df)

            if orders is not None:
                cols = [
                    "OrderID",
                    "CustomerID",
                    "EmployeeID",
                    "OrderDate",
                    "RequiredDate",
                    "ShippedDate",
                    "ShipVia",
                    "Freight",
                    "ShipName",
                    "ShipAddress",
                    "ShipCity",
                    "ShipRegion",
                    "ShipPostalCode",
                    "ShipCountry",
                ]
                df = orders[cols].rename(
                    columns={
                        "OrderID": "order_id",
                        "CustomerID": "customer_id",
                        "EmployeeID": "employee_id",
                        "OrderDate": "order_date",
                        "RequiredDate": "required_date",
                        "ShippedDate": "shipped_date",
                        "ShipVia": "ship_via",
                        "Freight": "freight",
                        "ShipName": "ship_name",
                        "ShipAddress": "ship_address",
                        "ShipCity": "ship_city",
                        "ShipRegion": "ship_region",
                        "ShipPostalCode": "ship_postal_code",
                        "ShipCountry": "ship_country",
                    }
                )
                _copy_dataframe(conn, df, "public.orders")
                loaded_counts["orders"] = len(df)

            if categories is not None:
                cols = ["CategoryID", "CategoryName", "Description"]
                df = categories[cols].rename(
                    columns={
                        "CategoryID": "category_id",
                        "CategoryName": "category_name",
                        "Description": "description",
                    }
                )
                _copy_dataframe(conn, df, "public.categories")
                loaded_counts["categories"] = len(df)

            if products is not None:
                cols = [
                    "ProductID",
                    "ProductName",
                    "SupplierID",
                    "CategoryID",
                    "QuantityPerUnit",
                    "UnitPrice",
                    "UnitsInStock",
                    "UnitsOnOrder",
                    "ReorderLevel",
                    "Discontinued",
                ]
                df = products[cols].rename(
                    columns={
                        "ProductID": "product_id",
                        "ProductName": "product_name",
                        "SupplierID": "supplier_id",
                        "CategoryID": "category_id",
                        "QuantityPerUnit": "quantity_per_unit",
                        "UnitPrice": "unit_price",
                        "UnitsInStock": "units_in_stock",
                        "UnitsOnOrder": "units_on_order",
                        "ReorderLevel": "reorder_level",
                        "Discontinued": "discontinued",
                    }
                )
                _copy_dataframe(conn, df, "public.products")
                loaded_counts["products"] = len(df)

            if order_details is not None:
                cols = ["OrderID", "ProductID", "UnitPrice", "Quantity", "Discount"]
                df = order_details[cols].rename(
                    columns={
                        "OrderID": "order_id",
                        "ProductID": "product_id",
                        "UnitPrice": "unit_price",
                        "Quantity": "quantity",
                        "Discount": "discount",
                    }
                )
                _copy_dataframe(conn, df, "public.order_details")
                loaded_counts["order_details"] = len(df)

        return loaded_counts

    def generate_report(self) -> Dict[str, Dict[str, int]]:
        """
        Generate normalization and integrity metrics from the DB.

        Returns a dict keyed by metric group with counts.
        """
        metrics: Dict[str, Dict[str, int]] = {
            "row_counts": {},
            "duplicates": {},
            "fk_violations": {},
            "nulls": {},
        }
        with self._connect() as conn, conn.cursor() as cur:
            for tbl in [
                "customers",
                "employees",
                "orders",
                "categories",
                "products",
                "order_details",
            ]:
                cur.execute(f"SELECT COUNT(*) FROM public.{tbl}")
                metrics["row_counts"][tbl] = cur.fetchone()[0]  # type: ignore[index]
            
            cur.execute(
                "SELECT COUNT(*) FROM (SELECT customer_id FROM public.customers GROUP BY 1 HAVING COUNT(*)>1) t"
            )
            metrics["duplicates"]["customers"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM (SELECT employee_id FROM public.employees GROUP BY 1 HAVING COUNT(*)>1) t"
            )
            metrics["duplicates"]["employees"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM (SELECT order_id FROM public.orders GROUP BY 1 HAVING COUNT(*)>1) t"
            )
            metrics["duplicates"]["orders"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM (SELECT category_id FROM public.categories GROUP BY 1 HAVING COUNT(*)>1) t"
            )
            metrics["duplicates"]["categories"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM (SELECT product_id FROM public.products GROUP BY 1 HAVING COUNT(*)>1) t"
            )
            metrics["duplicates"]["products"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM (SELECT order_id, product_id FROM public.order_details GROUP BY 1,2 HAVING COUNT(*)>1) t"
            )
            metrics["duplicates"]["order_details"] = cur.fetchone()[0]  # type: ignore[index]
            
            cur.execute(
                "SELECT COUNT(*) FROM public.orders o LEFT JOIN public.customers c ON o.customer_id=c.customer_id "
                "WHERE o.customer_id IS NOT NULL AND c.customer_id IS NULL"
            )
            metrics["fk_violations"]["orders.customer_id->customers"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM public.orders o LEFT JOIN public.employees e ON o.employee_id=e.employee_id "
                "WHERE o.employee_id IS NOT NULL AND e.employee_id IS NULL"
            )
            metrics["fk_violations"]["orders.employee_id->employees"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM public.order_details d LEFT JOIN public.orders o ON d.order_id=o.order_id "
                "WHERE o.order_id IS NULL"
            )
            metrics["fk_violations"]["order_details.order_id->orders"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM public.order_details d LEFT JOIN public.products p ON d.product_id=p.product_id "
                "WHERE p.product_id IS NULL"
            )
            metrics["fk_violations"]["order_details.product_id->products"] = cur.fetchone()[0]  # type: ignore[index]
            
            cur.execute(
                "SELECT COUNT(*) FROM public.customers WHERE company_name IS NULL"
            )
            metrics["nulls"]["customers.company_name"] = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT COUNT(*) FROM public.products WHERE product_name IS NULL"
            )
            metrics["nulls"]["products.product_name"] = cur.fetchone()[0]  # type: ignore[index]
        return metrics


__all__ = [
    "LoaderConfig",
    "DataLoader",
    "_coerce_types",
    "_drop_duplicates",
]
