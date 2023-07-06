from flask import Flask, render_template, request, redirect, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import uuid
import os
import openai
import requests
from pymongo import MongoClient

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tea58/BUCK/MAG'
OPENAI_API_KEY = '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'
CORS(app, origins='*')

# Connect to MongoDB Atlas
client = MongoClient('mongodb+srv://koushik:niyogi@cluster0.wfutoyr.mongodb.net/zomato-flask?retryWrites=true&w=majority')
db = client["zomato-Flask"]
menu_collection = db['menu']
orders_collection = db['orders']



def get_chatbot_response(query):
    """
    Sends a user query to OpenAI API and retrieves the chatbot's response.

    Args:
        query (str): User query.

    Returns:
        str: Chatbot's response.

    """
    print(query)
    prompt = f"User: {query}\nChatbot: Hi! How can I assist you today?\nUser: {query}\nChatbot:\n- What are your operation hours?|Our operation hours are from 9 AM to 6 PM.\n- What is the status of my order?|Please provide your order ID, and we will check the status for you.\n- What is your most popular dish?|Our most popular dish is the Spicy Chicken Pasta.\n\nUser:"

    payload = {
        'prompt': prompt,
        'max_tokens': 100
    }

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }

    response = requests.post(
        'https://api.openai.com/v1/engines/text-davinci-003/completions',
        data=json.dumps(payload),
        headers=headers
    )

    if response.status_code == 200:
        chatbot_response = response.json()['choices'][0]['text'].strip()
        return chatbot_response
    else:
        return "Oops! Something went wrong with the chatbot."

@app.route('/menu', methods=['GET'])
def display_menu():
    """
    Retrieves the menu from the MongoDB collection and returns it as a JSON response.

    Returns:
        JSON response containing the menu.

    """
    menu = list(menu_collection.find())
    return jsonify({"menu": menu})

@app.route('/add_dish', methods=['POST'])
def add_dish():
    """
    Adds a new dish to the menu collection in MongoDB.

    Returns:
        JSON response with a success message.

    """
    request_data = request.get_json()
    dish_id = str(uuid.uuid4())
    new_dish = {
        'id': dish_id,
        'name': request_data['name'],
        'price': request_data['price'],
        'availability': request_data['availability']
    }

    menu_collection.insert_one(new_dish)

    return jsonify({"msg" : "New dish has been added!!"})

@app.route('/remove_dish/<id>', methods=['DELETE'])
def remove_dish(id):
    """
    Removes a dish from the menu collection in MongoDB.

    Args:
        id (str): ID of the dish to be removed.

    Returns:
        JSON response with a success message.

    """
    menu_collection.delete_one({'id': id})

    return jsonify({"msg" : "Dish has been removed from the menu successfully!!"})

@app.route('/update_availability', methods=['POST'])
def update_availability():
    """
    Updates the availability status of a dish in the menu collection in MongoDB.

    Returns:
        JSON response with a success message.

    """
    request_data = request.get_json()

    menu_collection.update_one({'id': request_data['id']}, {'$set': {'availability': request_data['availability']}})

    return jsonify({"msg" : "Dish status has been updated successfully!!"})

@app.route('/take_order', methods=['POST'])
def take_order():
    """
    Takes a customer's order and adds it to the orders collection in MongoDB.

    Returns:
        JSON response with a success message.

    """
    request_data = request.get_json()

    dish = menu_collection.find_one({'id': request_data['id']})
    if dish:
        order_id = str(uuid.uuid4())
        new_order = {
            'id': order_id,
            'customer_name': request_data['name'],
            'dishes': request_data['dishes'],
            'price': dish['price'],
            'status': 'Received'
        }

        orders_collection.insert_one(new_order)

        return jsonify({'msg': 'Order taken successfully'})
    else:
        return jsonify({"msg" : "Ordered dish is not present at this moment"})

@app.route('/update_order', methods=['PATCH'])
def update_order():
    """
    Updates the status of an order in the orders collection in MongoDB.

    Returns:
        JSON response with a success message.

    """
    request_data = request.get_json()

    result = orders_collection.update_one({'id': request_data['id']}, {'$set': {'status': request_data['status']}})

    if result.modified_count > 0:
        # Emit the updated status to all connected clients

        return jsonify({'msg': 'Order status updated successfully'})
    else:
        return jsonify({"msg" : 'Order not found!!'})

@app.route('/review_orders', methods=['GET'])
def review_orders():
    """
    Retrieves all orders from the orders collection in MongoDB.

    Returns:
        JSON response containing the orders.

    """
    orders = list(orders_collection.find())
    return jsonify({'orders': orders})

@app.route('/add_review/<order_id>', methods=['PATCH'])
def add_review(order_id):
    """
    Adds a review to an order in the orders collection in MongoDB.

    Args:
        order_id (str): ID of the order.

    Returns:
        JSON response with a success message.

    """
    request_data = request.get_json()

    result = orders_collection.update_one(
        {'id': order_id},
        {'$set': {'rating': request_data['rating'], 'review': request_data['review']}}
    )

    if result.modified_count > 0:
        return jsonify({'msg': 'Review added successfully'})
    else:
        return jsonify({"msg" : 'Order not found!!'})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    """
    Retrieves the chatbot's response for a user query.

    Returns:
        JSON response containing the chatbot's response.

    """
    request_data = request.get_json()
    user_query = request_data['query']

    # Get the chatbot's response for the user query
    chatbot_response = get_chatbot_response(user_query)

    # Return the response as JSON
    return jsonify({'response': chatbot_response})


if __name__ == '__main__':
    app.run(debug=True)
