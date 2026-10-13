import sqlite3
from datetime import datetime
from pathlib import Path
import hashlib
import getpass

DB = Path("expense_tracker.db")

def connect():
    return sqlite3.connect(DB)

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount >= 0),
            note TEXT,
            date TEXT NOT NULL)""")
        con.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register():
    username = input("New username: ").strip()
    password = getpass.getpass("Password: ")
    try:
        with connect() as con:
            con.execute("INSERT INTO users(username,password) VALUES(?,?)",
                        (username, hash_password(password)))
        print("Registration successful.")
    except sqlite3.IntegrityError:
        print("Username already exists.")

def login():
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    with connect() as con:
        row = con.execute("SELECT username FROM users WHERE username=? AND password=?",
                          (username, hash_password(password))).fetchone()
    if row:
        print("Login successful.")
        return username
    print("Invalid credentials.")
    return None

def add_transaction(username):
    kind = input("Type (income/expense): ").strip().lower()
    if kind not in ("income", "expense"):
        print("Invalid type.")
        return
    category = input("Category: ").strip()
    try:
        amount = float(input("Amount: "))
        if amount < 0: raise ValueError
    except ValueError:
        print("Invalid amount.")
        return
    note = input("Note: ").strip()
    date = input("Date YYYY-MM-DD (Enter=today): ").strip() or datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date.")
        return
    with connect() as con:
        con.execute("""INSERT INTO transactions(username,kind,category,amount,note,date)
                       VALUES(?,?,?,?,?,?)""",
                    (username, kind, category, amount, note, date))
    print("Transaction added.")

def list_transactions(username):
    with connect() as con:
        rows = con.execute("""SELECT id,kind,category,amount,note,date
                              FROM transactions WHERE username=? ORDER BY date DESC,id DESC""",
                           (username,)).fetchall()
    if not rows:
        print("No transactions.")
        return
    print("-"*90)
    for r in rows:
        print(f"ID:{r[0]} | {r[5]} | {r[1].upper():7} | {r[2]:15} | ₹{r[3]:.2f} | {r[4]}")
    print("-"*90)

def update_transaction(username):
    list_transactions(username)
    try: tid = int(input("Transaction ID: "))
    except ValueError: print("Invalid ID."); return
    with connect() as con:
        row = con.execute("SELECT kind,category,amount,note,date FROM transactions WHERE id=? AND username=?",
                          (tid, username)).fetchone()
    if not row:
        print("Transaction not found."); return
    kind = input(f"Type [{row[0]}]: ").strip().lower() or row[0]
    category = input(f"Category [{row[1]}]: ").strip() or row[1]
    amount_raw = input(f"Amount [{row[2]}]: ").strip()
    amount = float(amount_raw) if amount_raw else row[2]
    note = input(f"Note [{row[3]}]: ").strip() or row[3]
    date = input(f"Date [{row[4]}]: ").strip() or row[4]
    with connect() as con:
        con.execute("""UPDATE transactions SET kind=?,category=?,amount=?,note=?,date=?
                       WHERE id=? AND username=?""",
                    (kind,category,amount,note,date,tid,username))
    print("Updated.")

def delete_transaction(username):
    try: tid = int(input("Transaction ID to delete: "))
    except ValueError: print("Invalid ID."); return
    with connect() as con:
        cur = con.execute("DELETE FROM transactions WHERE id=? AND username=?", (tid,username))
    print("Deleted." if cur.rowcount else "Transaction not found.")

def analytics(username):
    with connect() as con:
        income = con.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE username=? AND kind='income'",(username,)).fetchone()[0]
        expense = con.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE username=? AND kind='expense'",(username,)).fetchone()[0]
        rows = con.execute("""SELECT substr(date,1,7),kind,SUM(amount)
                              FROM transactions WHERE username=?
                              GROUP BY substr(date,1,7),kind ORDER BY substr(date,1,7)""",(username,)).fetchall()
    print(f"Total Income : ₹{income:.2f}")
    print(f"Total Expense: ₹{expense:.2f}")
    print(f"Balance      : ₹{income-expense:.2f}")
    print("\nMonthly summary:")
    for month, kind, total in rows:
        print(f"{month} | {kind:7} | ₹{total:.2f}")
    return income, expense

def export_report(username):
    import csv
    with connect() as con:
        rows = con.execute("""SELECT id,kind,category,amount,note,date FROM transactions
                              WHERE username=? ORDER BY date""",(username,)).fetchall()
    out = Path(f"{username}_expense_report.csv")
    with open(out,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["id","kind","category","amount","note","date"]); w.writerows(rows)
    print(f"Report exported to {out}")

def chart(username):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Install matplotlib: pip install matplotlib"); return
    with connect() as con:
        rows=con.execute("""SELECT category,SUM(amount) FROM transactions
                            WHERE username=? AND kind='expense' GROUP BY category""",(username,)).fetchall()
    if not rows: print("No expense data."); return
    labels=[r[0] for r in rows]; values=[r[1] for r in rows]
    plt.figure(figsize=(8,5))
    plt.bar(labels, values)
    plt.title("Expenses by Category")
    plt.xlabel("Category"); plt.ylabel("Amount")
    plt.xticks(rotation=30, ha="right"); plt.tight_layout()
    plt.savefig(f"{username}_expense_chart.png"); plt.show()

def user_menu(username):
    while True:
        print("\n=== EXPENSE TRACKER ===")
        print("1 Add transaction\n2 List transactions\n3 Update transaction\n4 Delete transaction")
        print("5 Analytics\n6 Generate chart\n7 Export CSV report\n8 Logout")
        c=input("Choice: ").strip()
        if c=="1": add_transaction(username)
        elif c=="2": list_transactions(username)
        elif c=="3": update_transaction(username)
        elif c=="4": delete_transaction(username)
        elif c=="5": analytics(username)
        elif c=="6": chart(username)
        elif c=="7": export_report(username)
        elif c=="8": break
        else: print("Invalid choice.")

def main():
    init_db()
    while True:
        print("\n=== EXPENSE TRACKER & ANALYTICS SYSTEM ===")
        print("1 Register\n2 Login\n3 Exit")
        c=input("Choice: ").strip()
        if c=="1": register()
        elif c=="2":
            user=login()
            if user: user_menu(user)
        elif c=="3": break
        else: print("Invalid choice.")

if __name__=="__main__":
    main()
