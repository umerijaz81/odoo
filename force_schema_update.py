import sys

def force_schema(env):
    cr = env.cr
    print("--- Starting Schema Patch ---")
    
    # hr_employee
    try:
        cr.execute("ALTER TABLE hr_employee ADD COLUMN IF NOT EXISTS bank_account VARCHAR")
        cr.execute("ALTER TABLE hr_employee ADD COLUMN IF NOT EXISTS vacation_days_used FLOAT")
        cr.execute("ALTER TABLE hr_employee ADD COLUMN IF NOT EXISTS vacation_days_available FLOAT")
        print("SUCCESS: hr_employee updated")
    except Exception as e:
        print(f"ERROR on hr_employee: {e}")
        cr.rollback()

    # nordic_payslip
    try:
        cr.execute("ALTER TABLE nordic_payslip ADD COLUMN IF NOT EXISTS run_number INTEGER")
        cr.execute("ALTER TABLE nordic_payslip ADD COLUMN IF NOT EXISTS payment_date DATE")
        print("SUCCESS: nordic_payslip updated")
    except Exception as e:
        print(f"ERROR on nordic_payslip: {e}")
        cr.rollback()

    # nordic_salary_rule
    try:
        cr.execute("ALTER TABLE nordic_salary_rule ADD COLUMN IF NOT EXISTS tax_code VARCHAR")
        cr.execute("ALTER TABLE nordic_salary_rule ADD COLUMN IF NOT EXISTS is_vacation_base BOOLEAN")
        print("SUCCESS: nordic_salary_rule updated")
    except Exception as e:
        print(f"ERROR on nordic_salary_rule: {e}")
        cr.rollback()

    # nordic_payslip_line
    try:
        cr.execute("ALTER TABLE nordic_payslip_line ADD COLUMN IF NOT EXISTS tax_code VARCHAR")
        cr.execute("ALTER TABLE nordic_payslip_line ADD COLUMN IF NOT EXISTS is_vacation_base BOOLEAN")
        print("SUCCESS: nordic_payslip_line updated")
    except Exception as e:
        print(f"ERROR on nordic_payslip_line: {e}")
        cr.rollback()

    cr.commit()
    print("--- Schema Patch Completed ---")

if __name__ == "__main__":
    # This part depends on how odoo shell passes env
    # In 'odoo-bin shell -c script.py', env is available as 'obj' or 'self'
    pass
