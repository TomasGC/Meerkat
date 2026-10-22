class ReportRenderer:
    def render_html(self, rows):
        cells = "".join(f"<tr><td>{r['item']}</td><td>{r['total']}</td></tr>" for r in rows)
        return f"<table>{cells}</table>"
