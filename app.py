import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# ---------------- DB SETUP ----------------
conn = sqlite3.connect("shop.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT UNIQUE,
    name TEXT,
    cost_price REAL,
    selling_price REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sales(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    quantity INTEGER,
    date TEXT,
    UNIQUE(product_id, date)
)
""")

conn.commit()

# ---------------- UI ----------------
st.title("Daily Profit Tracker")

menu = st.radio("Menu", ["Add Product", "Daily Entry", "Dashboard"])

# ---------------- ADD PRODUCT ----------------
if menu == "Add Product":
    st.header("Add Product")

    pid = st.text_input("Product ID")
    name = st.text_input("Product Name")
    cost = st.number_input("Getting Price (Company)", min_value=0.0)
    sell = st.number_input("Selling Price", min_value=0.0)

    if st.button("Add Product"):
        try:
            cur.execute(
                "INSERT INTO products(product_id,name,cost_price,selling_price) VALUES (?,?,?,?)",
                (pid, name, cost, sell)
            )
            conn.commit()
            st.success("Product added")
        except:
            st.error("Product ID already exists")

# ---------------- DAILY ENTRY ----------------
elif menu == "Daily Entry":
    st.header("Enter Today's Quantity")

    products = pd.read_sql("SELECT * FROM products", conn)
    today = str(date.today())

    if products.empty:
        st.warning("Add products first")
    else:
        for _, row in products.iterrows():

            existing = cur.execute(
                "SELECT quantity FROM sales WHERE product_id=? AND date=?",
                (row["product_id"], today)
            ).fetchone()

            default_qty = existing[0] if existing else 0

            qty = st.number_input(
                f"{row['name']} (Sell Qty)",
                min_value=0,
                value=default_qty,
                key=f"{row['product_id']}_{today}_{row['id']}"
            )

            col1, col2, col3 = st.columns(3)

            # SAVE / UPDATE
            with col1:
                if st.button("Save", key=f"save_{row['id']}"):
                    if existing:
                        cur.execute(
                            "UPDATE sales SET quantity=? WHERE product_id=? AND date=?",
                            (qty, row["product_id"], today)
                        )
                    else:
                        cur.execute(
                            "INSERT INTO sales(product_id,quantity,date) VALUES (?,?,?)",
                            (row["product_id"], qty, today)
                        )
                    conn.commit()
                    st.success(f"{row['name']} saved")

            # DELETE SALES ENTRY (today)
            with col2:
                if st.button("Delete Entry", key=f"del_entry_{row['id']}"):
                    cur.execute(
                        "DELETE FROM sales WHERE product_id=? AND date=?",
                        (row["product_id"], today)
                    )
                    conn.commit()
                    st.warning(f"{row['name']} entry deleted")

            # DELETE PRODUCT COMPLETELY
            with col3:
                if st.button("Delete Product", key=f"del_prod_{row['id']}"):
                    cur.execute(
                        "DELETE FROM products WHERE product_id=?",
                        (row["product_id"],)
                    )
                    cur.execute(
                        "DELETE FROM sales WHERE product_id=?",
                        (row["product_id"],)
                    )
                    conn.commit()
                    st.error(f"{row['name']} removed completely")

            # -------- EDIT PRODUCT --------
            with st.expander(f"Edit {row['name']}"):
                new_cost = st.number_input(
                    "New Cost Price",
                    value=row["cost_price"],
                    key=f"cost_{row['id']}"
                )
                new_sell = st.number_input(
                    "New Selling Price",
                    value=row["selling_price"],
                    key=f"sell_{row['id']}"
                )

                if st.button("Update Price", key=f"update_{row['id']}"):
                    cur.execute(
                        "UPDATE products SET cost_price=?, selling_price=? WHERE product_id=?",
                        (new_cost, new_sell, row["product_id"])
                    )
                    conn.commit()
                    st.success("Updated successfully")

# ---------------- DASHBOARD ----------------
elif menu == "Dashboard":
    st.header("Today's Profit Report")

    products = pd.read_sql("SELECT * FROM products", conn)
    sales = pd.read_sql("SELECT * FROM sales", conn)

    today = str(date.today())

    report = []
    total_profit = 0
    total_company_bill = 0
    total_sales_amount = 0

    for _, p in products.iterrows():
        pid = p["product_id"]

        today_sales = sales[
            (sales["product_id"] == pid) & (sales["date"] == today)
        ]

        qty = today_sales["quantity"].sum()

        cost_total = p["cost_price"] * qty
        sales_total = p["selling_price"] * qty
        profit = sales_total - cost_total

        total_profit += profit
        total_company_bill += cost_total
        total_sales_amount += sales_total

        report.append({
            "Product": p["name"],
            "Sold Qty": qty,
            "Cost Price": p["cost_price"],
            "Selling Price": p["selling_price"],
            "Company Bill": cost_total,
            "Sales Amount": sales_total,
            "Profit": profit
        })

    df = pd.DataFrame(report)
    st.dataframe(df)

    st.subheader(f"Total Company Bill: ₹ {total_company_bill}")
    st.subheader(f"Total Sales Amount: ₹ {total_sales_amount}")
    st.subheader(f"Total Profit: ₹ {total_profit}")
