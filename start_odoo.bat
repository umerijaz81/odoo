@echo off
set PATH=C:\Program Files\wkhtmltopdf\bin;%PATH%
echo Running Odoo 19 with Wkhtmltopdf path: C:\Program Files\wkhtmltopdf\bin
.\venv\Scripts\python.exe odoo-bin -c odoo.conf -d my_dev_db --http-interface=0.0.0.0
