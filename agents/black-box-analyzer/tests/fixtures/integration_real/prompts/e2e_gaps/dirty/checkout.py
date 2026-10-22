from flask import Flask, jsonify, request

app = Flask(__name__)


@app.post("/checkout")
def checkout():
    cart = load_cart(request.json["cart_id"])
    order = place_order(cart)
    send_confirmation(order)
    return jsonify({"order_id": order.id}), 201
