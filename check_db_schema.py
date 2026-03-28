import psycopg2

def check_db():
    try:
        conn = psycopg2.connect(
            dbname="my_dev_db",
            user="odoo",
            password="odoo",
            host="localhost",
            port="5435"
        )
        cur = conn.cursor()
        
        tables = ['hr_employee', 'nordic_payslip', 'nordic_salary_rule', 'nordic_payslip_line']
        for table in tables:
            print(f"--- Table: {table} ---")
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
            columns = [row[0] for row in cur.fetchall()]
            for col in columns:
                print(f"  {col}")
            print("\n")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
