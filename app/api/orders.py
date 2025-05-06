from flask_restx import Resource, fields, Namespace
from flask import request, jsonify
from app.api import api
from db.database import get_db
from db.models import Order, OrderItem, Book
from app.schemas import OrderCreate, OrderResponse, OrderUpdate
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from http import HTTPStatus

# Create namespace
ns = Namespace("orders", description="Order operations")

# Define models for Swagger documentation
order_item_model = api.model(
    "OrderItem",
    {
        "book_id": fields.Integer(required=True, description="Book ID"),
        "quantity": fields.Integer(required=True, description="Quantity"),
        "price": fields.Float(description="Price at time of order"),
    },
)

order_model = api.model(
    "Order",
    {
        "id": fields.Integer(description="Order ID"),
        "user_id": fields.Integer(description="User ID"),
        "status": fields.String(description="Order status"),
        "total_amount": fields.Float(description="Total order amount"),
        "shipping_address": fields.String(required=True, description="Shipping address"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
        "items": fields.List(fields.Nested(order_item_model)),
    },
)


@ns.route("/")
class OrderList(Resource):
    @login_required
    @ns.doc("list_orders")
    @ns.marshal_list_with(order_model)
    def get(self):
        """List all orders for the current user"""
        db = get_db()
        orders = db.query(Order).filter(Order.user_id == current_user.id).all()
        return [OrderResponse.from_orm(order).dict() for order in orders]

    @login_required
    @ns.doc("create_order")
    @ns.expect(order_model)
    @ns.marshal_with(order_model, code=201)
    def post(self):
        """Create a new order"""
        try:
            # Validate input data
            order_data = OrderCreate(**api.payload)
            db = get_db()

            # Calculate total amount and validate books
            total_amount = 0
            order_items = []

            for item in order_data.items:
                book = db.query(Book).filter(Book.id == item.book_id).first()
                if not book:
                    return {"error": f"Book with ID {item.book_id} not found"}, 404

                total_amount += book.price * item.quantity
                order_items.append({"book_id": book.id, "quantity": item.quantity, "price": book.price})

            # Create order
            order = Order(
                user_id=current_user.id, shipping_address=order_data.shipping_address, total_amount=total_amount
            )
            db.add(order)
            db.flush()  # Get order ID

            # Create order items
            for item in order_items:
                order_item = OrderItem(
                    order_id=order.id, book_id=item["book_id"], quantity=item["quantity"], price=item["price"]
                )
                db.add(order_item)

            db.commit()
            return OrderResponse.from_orm(order).dict(), 201

        except SQLAlchemyError as e:
            db.rollback()
            return {"error": str(e)}, 400


@ns.route("/<int:id>")
class OrderResource(Resource):
    @login_required
    @ns.doc("get_order")
    @ns.marshal_with(order_model)
    def get(self, id):
        """Get an order by ID"""
        db = get_db()
        order = db.query(Order).filter(Order.id == id, Order.user_id == current_user.id).first()
        if not order:
            return {"error": "Order not found"}, 404
        return OrderResponse.from_orm(order).dict()

    @login_required
    @ns.doc("update_order")
    @ns.expect(order_model)
    @ns.marshal_with(order_model)
    def put(self, id):
        """Update an order (only status and shipping address can be updated)"""
        db = get_db()
        order = db.query(Order).filter(Order.id == id, Order.user_id == current_user.id).first()
        if not order:
            return {"error": "Order not found"}, 404

        try:
            update_data = OrderUpdate(**request.json)
            if update_data.status:
                order.status = update_data.status
            if update_data.shipping_address:
                order.shipping_address = update_data.shipping_address

            db.commit()
            return OrderResponse.from_orm(order).dict()

        except SQLAlchemyError as e:
            db.rollback()
            return {"error": str(e)}, 400
