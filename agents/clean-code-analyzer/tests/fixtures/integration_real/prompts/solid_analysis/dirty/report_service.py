import smtplib


class ReportService:
    def __init__(self, db):
        self.db = db

    def load_rows(self, month):
        return self.db.query("SELECT item, total FROM sales WHERE month = ?", month)

    def render_html(self, rows):
        cells = "".join(f"<tr><td>{r['item']}</td><td>{r['total']}</td></tr>" for r in rows)
        return f"<table>{cells}</table>"

    def email(self, html, to):
        with smtplib.SMTP("localhost") as server:
            server.sendmail("reports@example.com", to, html)
