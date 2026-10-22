from flask import Flask, jsonify
from flask_login import current_user, login_required

app = Flask(__name__)


@app.get("/invoices/<int:invoice_id>")
@login_required
def get_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, owner_id=current_user.id).first_or_404()
    return jsonify(invoice.to_dict())
