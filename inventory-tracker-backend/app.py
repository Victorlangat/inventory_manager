from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import datetime
import uuid

app = Flask(__name__)
CORS(app)

# Default users
users = {
    "victorjames": {"password": "tictac20", "role": "admin"}
}

inventory_data = []
sales_data = []
orders = []

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        user = users.get(username)
        if user and user['password'] == password:
            return jsonify({"message": "Login successful", "role": user['role']}), 200
        else:
            return jsonify({"error": "Invalid username or password"}), 401
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<int:order_id>/arrived', methods=['POST'])
def order_arrived(order_id):
    try:
        order = next((o for o in orders if o.get('id') == order_id), None)
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Check if the item already exists in the inventory
        inventory_item = next((item for item in inventory_data if item['product'] == order['product']), None)
        if inventory_item:
            inventory_item['quantity'] += order['quantity']
        else:
            new_inventory_item = {
                "id": str(uuid.uuid4()),  # Generate a new unique ID
                "product": order['product'],
                "quantity": order['quantity'],
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            inventory_data.append(new_inventory_item)

        orders.remove(order)
        return jsonify({"message": "Order marked as arrived and inventory updated"}), 200
    except Exception as e:
        print(f"Error updating order: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    return jsonify(inventory_data)

@app.route('/api/inventory', methods=['POST'])
def add_inventory():
    try:
        new_inventory_item = request.json

        # Check if the item already exists in the inventory
        inventory_item = next((item for item in inventory_data if item['product'] == new_inventory_item['product']), None)
        if inventory_item:
            # Update the existing inventory item's quantity
            inventory_item['quantity'] += new_inventory_item['quantity']
        else:
            # Add the new inventory item with a unique ID
            new_inventory_item["id"] = str(uuid.uuid4())  # Generate a new unique ID
            inventory_data.append(new_inventory_item)

        return jsonify({"message": "Inventory updated successfully"}), 200
    except Exception as e:
        print(f"Error updating inventory: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sales', methods=['POST'])
def add_sale():
    try:
        sale = request.json
        for sold_item in sale:
            inventory_item = next((item for item in inventory_data if item['product'] == sold_item['product']), None)
            if inventory_item and inventory_item['quantity'] >= sold_item['quantity']:
                inventory_item['quantity'] -= sold_item['quantity']
                sales_data.append({
                    "product": sold_item['product'],
                    "quantity": sold_item['quantity'],
                    "date": sold_item.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))  # Include the sale date
                })
            else:
                return jsonify({"error": f"Not enough stock for {sold_item['product']}"}), 400
        return jsonify({"message": "Sale recorded successfully"}), 200
    except Exception as e:
        print(f"Error recording sale: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sales', methods=['GET'])
def get_sales():
    return jsonify(sales_data)

@app.route('/api/orders', methods=['POST'])
def add_order():
    try:
        order = request.json
        orders.append(order)
        return jsonify({"message": "Order placed successfully"}), 200
    except Exception as e:
        print(f"Error placing order: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    return jsonify(orders)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = file.filename
        filepath = os.path.join('./uploads', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)

        # Load the file data
        with open(filepath, 'r') as f:
            file_data = json.load(f)

        # Merge file data with the existing inventory data
        for new_item in file_data:
            inventory_item = next((item for item in inventory_data if item['product'] == new_item['product']), None)
            if inventory_item:
                inventory_item['quantity'] += new_item['quantity']
            else:
                new_item['id'] = str(uuid.uuid4())  # Assign a unique ID
                inventory_data.append(new_item)

        return jsonify({"message": "File uploaded and inventory updated successfully"}), 200

@app.route('/api/files', methods=['GET'])
def get_files():
    files = os.listdir('./uploads')
    return jsonify(files)

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        filepath = os.path.join('./uploads', filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                file_data = json.load(f)

            # Subtract file data quantities from the inventory
            for item in file_data:
                inventory_item = next((inv_item for inv_item in inventory_data if inv_item['product'] == item['product']), None)
                if inventory_item:
                    inventory_item['quantity'] -= item['quantity']
                    if inventory_item['quantity'] <= 0:
                        inventory_data.remove(inventory_item)

            os.remove(filepath)
            return jsonify({"message": "File deleted and inventory updated successfully"}), 200
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        print(f"Error deleting file: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
