import json
from pathlib import Path
from flask import Flask, jsonify, request
from db import get_tracked_products_for_scraping, upsert_product
import notify_discord

app = Flask(__name__)
STORES_PATH = Path(__file__).parent / "stores.json"


def load_stores():
    return json.loads(STORES_PATH.read_text())


@app.route('/api/stores', methods=['GET'])
def get_stores():
    stores = load_stores()
    public = {
        key: {k: v for k, v in cfg.items() if k != 'discordWebhook'}
        for key, cfg in stores.items()
    }
    return jsonify(public)


@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(get_tracked_products_for_scraping())


@app.route('/api/price', methods=['POST'])
def post_price():
    data = request.get_json()
    upsert_product({
        'id': data['id'],
        'store': data['store'],
        'name': data['name'],
        'price': data['price'],
        'url': data['url'],
    })
    notify_discord.main()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
