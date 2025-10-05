-- Northwind 3NF skeleton; to be expanded during normalization step
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(10) PRIMARY KEY,
    company_name TEXT NOT NULL,
    contact_name TEXT,
    contact_title TEXT,
    address TEXT,
    city TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    phone TEXT,
    fax TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id INTEGER PRIMARY KEY,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    title TEXT,
    title_of_courtesy TEXT,
    birth_date DATE,
    hire_date DATE,
    address TEXT,
    city TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    home_phone TEXT,
    extension TEXT,
    notes TEXT,
    reports_to INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id VARCHAR(10) REFERENCES customers(customer_id),
    employee_id INTEGER REFERENCES employees(employee_id),
    order_date DATE,
    required_date DATE,
    shipped_date DATE,
    ship_via INTEGER,
    freight NUMERIC(12,2),
    ship_name TEXT,
    ship_address TEXT,
    ship_city TEXT,
    ship_region TEXT,
    ship_postal_code TEXT,
    ship_country TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    supplier_id INTEGER,
    category_id INTEGER REFERENCES categories(category_id),
    quantity_per_unit TEXT,
    unit_price NUMERIC(12,2),
    units_in_stock INTEGER,
    units_on_order INTEGER,
    reorder_level INTEGER,
    discontinued INTEGER CHECK (discontinued IN (0,1)),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_details (
    order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(product_id),
    unit_price NUMERIC(12,2) NOT NULL,
    quantity INTEGER NOT NULL,
    discount NUMERIC(5,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (order_id, product_id)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_orders_orderdate ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_customers_country ON customers(country);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_employee ON orders(employee_id);
CREATE INDEX IF NOT EXISTS idx_order_details_product ON order_details(product_id);

