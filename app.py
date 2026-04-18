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

            # Check existing quantity
            existing = cur.execute(
                "SELECT quantity FROM sales WHERE product_id=? AND date=?",
                (row["product_id"], today)
            ).fetchone()

            default_qty = existing[0] if existing else 0

            qty = st.number_input(
                f"{row['name']} (Sell Qty)",
                min_value=0,
                value=default_qty,
                key=f"{row['product_id']}_{today}_{row['id']}"   # FIXED KEY
            )

            if st.button(f"Save {row['name']}", key=f"btn_{row['id']}"):
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

# ---------------- DASHBOARD ----------------
elif menu == "Dashboard":
    st.header("Today's Profit Report")

    products = pd.read_sql("SELECT * FROM products", conn)
    sales = pd.read_sql("SELECT * FROM sales", conn)

    today = str(date.today())

    if products.empty:
        st.warning("No products available")
    else:
        report = []
        total_profit = 0

        for _, p in products.iterrows():
            pid = p["product_id"]

            today_sales = sales[
                (sales["product_id"] == pid) & (sales["date"] == today)
            ]

            total_qty = today_sales["quantity"].sum()

            profit_per_unit = p["selling_price"] - p["cost_price"]
            profit = profit_per_unit * total_qty

            total_profit += profit

            report.append({
                "Product ID": pid,
                "Name": p["name"],
                "Cost": p["cost_price"],
                "Selling": p["selling_price"],
                "Sold Qty": total_qty,
                "Profit": profit
            })

        df = pd.DataFrame(report)
        st.dataframe(df)

        st.subheader(f"Total Profit Today: ₹ {total_profit}")

        # Reset button
        if st.button("Reset Today Data"):
            cur.execute("DELETE FROM sales WHERE date=?", (today,))
            conn.commit()
            st.warning("Today's data cleared")