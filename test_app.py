import pytest
import os
from flask import Flask
from pymongo import MongoClient

# Import your Flask app, menu_collection, orders_collection, and user_collection from your application file
from app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# Define a PyTest fixture named setup_teardown for setup and teardown actions


def test_menu(client):
   response = client.get("/menu")
   assert response.status_code == 200
   assert len(response.json["menu"]) >= 0

def test_users(client):
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json["menu"]) >= 0

def test_review_order(client):
    response = client.get("/review_orders")
    assert response.status_code == 200
    assert len(response.json["menu"]) >= 0

def test_add_dish(client):
    data = {
        "name" : "Masala Dosa",
        "price" : 50,
        "availability" : True
    }
    menu_response = client.get("/menu")
    flag = False
    for dish in menu_response.json["menu"]:
        if data["name"] in dish["name"]:
            flag = True
            break

    if flag == True:
        assert True
    else:
        response = client.post("/add_dish",json = data)
        assert response.status_code == 200
        assert response.json == {"msg" : "New dish has been added!!"}

def test_remove_dish(client):

    menu = client.get("/menu")
    req_id = ""
    for dish in menu.json["menu"]:
        if dish["name"] == "Masala Dosa":
            req_id = dish['id']
            break
    response = client.delete(f'/remove_dish/{req_id}')
    assert response.status_code == 200
    assert response.json == {"msg" : "Dish has been removed from the menu successfully!!"}

def test_update_dish(client):
    data = {
        "name" : "Masala Dosa",
        "price" : 50,
        "availability" : True
    }
    post_data = client.post("/add_dish",json = data)
    menu = client.get("/menu")
    req_id = ""
    for dish in menu.json["menu"]:
        if dish["name"] == data["name"]:
            req_id = dish['id']
            break
    update_data = {"id":req_id,"availability" : False}
    response = client.post("/update_availability",json = update_data)
    assert response.status_code == 200
    assert response.json == {"msg" : "Dish status has been updated successfully!!"}
    remove_response = client.delete(f'/remove_dish/{req_id}')

def test_chatbot(client):
    response1 = client.post("/chatbot",json = {"query" : "What is operation hours"})
    assert response1.status_code == 200
    assert response1.data.decode('utf-8') == '{"response":"What are your operation hours?\\n Our operation hours are from 9 AM to 6 PM."}\n'
   
def test_take_order(client):
    dish_data = {
        "name" : "Masala Dosa",
        "price" : 50,
        "availability" : True
    }
    post_data = client.post("/add_dish",json = dish_data)
    menu = client.get("/menu")
    req_id = ""
    for dish in menu.json["menu"]:
        if dish["name"] == dish_data["name"]:
            req_id = dish['id']
            break
    data = {
        "name" : "koushik niyogi",
        'dishes': dish_data["name"],
        'id': req_id,
        'price': dish_data['price'],
        'userid': "176725diowwamddj",
    }
    response = client.post('/take_order',json = data)
    assert response.status_code == 200
    assert response.json == {'msg': 'Order taken successfully'}

def test_update_availability(client):
    req_id = ""
    order_data = client.get("/review_orders")
    for order in order_data.json["menu"]:
        if order['dishes'] == "Masala Dosa" and order["userid"] == "176725diowwamddj":
            req_id = order['id']
            break
    data = {
        "id" : req_id,
        "status" : "Preparing"
    }
    response = client.patch('/update_order',json = data)
    assert response.status_code == 200;
    assert response.json == {'msg': 'Order status updated successfully'}

def test_add_review(client):
    req_id = ""
    req_data = {}
    order_data = client.get("/review_orders")
    for order in order_data.json["menu"]:
        if order['dishes'] == "Masala Dosa" and order["userid"] == "176725diowwamddj":
            req_id = order['id']
            req_data = order
            break
    data = {
        "review" : "Good food",
        "rating" : 4.7
    }

    response = client.patch(f"/add_review/{req_id}",json = data)
    assert response.status_code == 200
    assert response.json == {'msg': 'Review added successfully'}
    client.delete(f'/remove_order/{req_id}')
    client.delete(f'/remove_dish/{req_data["dishid"]}')


    

    
