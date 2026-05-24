from flask import Flask, jsonify, request
from db import get_tracked_products_for_scraping, upsert_product
import notify_discord

app = Flask(__name__)


@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(get_tracked_products_for_scraping())


@app.route('/api/price', methods=['POST'])
def post_price():
    data = request.get_json()
    upsert_product({
        'productVariantID': data['id'],
        'name': data['name'],
        'price': data['price'],
        'url': data['url'],
    })
    notify_discord.main()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
