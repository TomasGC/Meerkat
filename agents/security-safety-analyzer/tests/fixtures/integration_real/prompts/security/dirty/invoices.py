from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/invoices/<int:invoice_id>")
def get_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return jsonify(invoice.to_dict())
