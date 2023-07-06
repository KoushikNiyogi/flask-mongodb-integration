from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from bson import json_util, ObjectId
import json
import uuid
import os
import openai
from dotenv import load_dotenv
import requests
from pymongo import MongoClient
import requests
import json
import logging
from logging.handlers import RotatingFileHandler


app = Flask(__name__)
socketio = SocketIO(app)
load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CORS(app, origins='*')

# Connect to MongoDB Atlas
MONGO_URL = os.environ.get("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client['zomato-Flask']
menu_collection = db['menu']
orders_collection = db['orders']
user_collection = db["users"]

def serialize_docs(docs):
    serialized_docs = []
    for doc in docs:
        doc['_id'] = str(doc['_id'])
        serialized_docs.append(doc)
    return serialized_docs

print(OPENAI_API_KEY)

handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)


def get_chatbot_response(query):
    prompt =  prompt = f"Food Delivery Chatbot:\nUser: {query}\nChatbot:"
    payload = {
        'prompt': prompt,
        'max_tokens': 100,
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
        if 'operation hours' in query.lower():
            chatbot_response = "What are your operation hours?\n Our operation hours are from 9 AM to 6 PM."
        elif 'status of my order' in query.lower():
            chatbot_response = "What is my order status?\n Please provide your order ID, and we will check the status for you."
        elif 'popular dish' in query.lower():
            chatbot_response = "What is popular dish here?\n Our most popular dish is the Spicy Chicken Pasta."
        # Add more custom question keywords and corresponding responses
        elif 'delivery options' in query.lower():
            chatbot_response = "What are delivery options available here?\n We offer multiple delivery options, including standard delivery and express delivery."
        elif 'payment methods' in query.lower():
            chatbot_response = "What payment methods do you accept?\n We accept various payment methods such as credit cards, debit cards, and digital wallets."
        elif 'menu' in query.lower():
            chatbot_response = "What is on the menu?\n You can find our menu on our website or in the app. It includes a wide range of delicious dishes."
        # Add more custom question keywords and corresponding responses here
        else:
            chatbot_response = f"{query}?\n I'm sorry, but I don't have the information you're looking for. Can I help you with anything else?"
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
    serialized_menu = serialize_docs(menu)
    return jsonify({"menu": serialized_menu})


@app.route('/users', methods=['GET'])
def display_users():
    users = list(user_collection.find())
    serialized_users = serialize_docs(users)
    return jsonify({"menu": serialized_users})
   

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
    print(request_data["id"]);
    dish = menu_collection.find_one({'id': request_data['id']})
    if dish:
        order_id = str(uuid.uuid4())
        new_order = {
            'id': order_id,
            'customer_name': request_data['name'],
            'dishes': request_data['dishes'],
            'dishid': request_data['id'],
            'price': dish['price'],
            'userid':request_data['userid'],
            'status': 'Received'
        }

        orders_collection.insert_one(new_order)

        return jsonify({'msg': 'Order taken successfully'})
    else:
        return jsonify({"msg" : dish})

@app.route('/update_order', methods=['PATCH'])
def update_order():
    """
    Updates the status of an order in the orders collection in MongoDB.

    Returns:
        JSON response with a success message.

    """
    request_data = request.get_json()
    order = orders_collection.find_one({'id': request_data['id']})
    result = orders_collection.update_one({'id': request_data['id']}, {'$set': {'status': request_data['status']}})

    if result.modified_count > 0:
        # Emit the updated status to all connected clients
        socketio.emit('order_status_changed', {'order_id': order["id"], 'status': request_data["status"]})
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
    serialized_orders = serialize_docs(orders)
    return jsonify({"menu": serialized_orders})

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
    review = request_data.get('review')
    rating = request_data.get('rating')
    order = orders_collection.find_one({'id': order_id})
    print(order)
    menu = menu_collection.find_one({'id':order['dishid']})
    if order is not None:
       if 'reviews' in menu and 'ratings' in menu:
            menu_collection.update_one(
                {'id': order["dishid"]},
                {
                    '$push': {
                        'reviews': review,
                        'ratings': rating
                    }
                }
            )
       else:
            menu_collection.update_one(
                {'id': order["dishid"]},
                {
                    '$set': {
                        'reviews': [review],
                        'ratings': [rating]
                    }
                }
            )
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
    socketio.run(app)
