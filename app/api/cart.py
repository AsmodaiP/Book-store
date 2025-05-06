from flask import request
from flask_restx import Resource, Namespace, fields
from flask_login import login_required, current_user
from http import HTTPStatus
from db.models import Cart, CartItem, Book, Order, OrderItem, OrderStatus
from app.schemas import CartItemCreate, CartResponse, OrderCreate
from db.database import get_db, session_scope
from sqlalchemy import func
from sqlalchemy.exc import OperationalError
import time

ns = Namespace("cart", description="Cart operations")




# Swagger models
cart_item_model = ns.model(
    "CartItem",
    {
        "book_id": fields.Integer(required=True, description="Book ID"),
        "quantity": fields.Integer(required=True, description="Quantity", min=1),
    },
)

# Model for updating quantity only (for PUT /cart/items/{book_id})
cart_item_update_model = ns.model(
    "CartItemUpdate",
    {
        "quantity": fields.Integer(required=True, description="Quantity", min=1),
    },
)

cart_response_model = ns.model(
    "CartResponse",
    {
        "id": fields.Integer(description="Cart ID"),
        "user_id": fields.Integer(description="User ID"),
        "items": fields.List(fields.Nested(cart_item_model)),
        "total_price": fields.Float(description="Total cart price"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
    },
)


def get_cart_response():
    """Helper function to get cart response"""
    with session_scope() as db:
        cart = db.query(Cart).filter_by(user_id=current_user.id).first()
        if not cart:
            cart = Cart(user_id=current_user.id)
            db.add(cart)
            db.commit()

        # Calculate total price
        total_price = (
            db.query(func.sum(Book.price * CartItem.quantity))
            .join(CartItem, Book.id == CartItem.book_id)
            .filter(CartItem.cart_id == cart.id)
            .scalar()
            or 0.0
        )

        # Create response dictionary before closing session
        response = {
            "id": cart.id,
            "user_id": cart.user_id,
            "items": [{"book_id": item.book_id, "quantity": item.quantity} for item in cart.items],
            "total_price": total_price,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at,
        }
        return response


@ns.route("")
class CartResource(Resource):

    @ns.doc("get_cart", description="Получить корзину текущего пользователя.")
    @ns.marshal_with(cart_response_model)
    @login_required
    def get(self):
        """Get current user's cart"""
        return get_cart_response()

    @ns.doc("add_to_cart", description="Добавить товар в корзину.")
    @ns.expect(cart_item_model)
    @ns.marshal_with(cart_response_model)
    @login_required
    def post(self):
        """Add item to cart"""
        with session_scope() as db:
            data = CartItemCreate(**request.json)

            # Check if book exists
            book = db.query(Book).get(data.book_id)
            if not book:
                return {"message": "Book not found"}, HTTPStatus.NOT_FOUND

            # Get or create cart
            cart = db.query(Cart).filter_by(user_id=current_user.id).first()
            if not cart:
                cart = Cart(user_id=current_user.id)
                db.add(cart)
                db.commit()

            # Check if item already in cart
            cart_item = db.query(CartItem).filter_by(cart_id=cart.id, book_id=data.book_id).first()

            if cart_item:
                cart_item.quantity += data.quantity
            else:
                cart_item = CartItem(cart_id=cart.id, book_id=data.book_id, quantity=data.quantity)
                db.add(cart_item)

            db.commit()
            return get_cart_response()

    @ns.doc("clear_cart", description="Очистить корзину пользователя.")
    @ns.marshal_with(cart_response_model)
    @login_required
    def delete(self):
        """Clear the entire cart"""
        with session_scope() as db:
            cart = db.query(Cart).filter_by(user_id=current_user.id).first()
            if not cart:
                return {"message": "Cart not found"}, HTTPStatus.NOT_FOUND

            # Delete all cart items
            db.query(CartItem).filter_by(cart_id=cart.id).delete()
            db.commit()
            return get_cart_response()

    @ns.doc("make_an_order", description="Оформить заказ из корзины пользователя.")
    @ns.expect(
        ns.model("OrderCreate", {"shipping_address": fields.String(required=True, description="Shipping address")})
    )
    @login_required
    def put(self):
        """Create an order from cart items"""
        with session_scope() as db:
            if not request.json or "shipping_address" not in request.json:
                return {"message": "Shipping address is required"}, HTTPStatus.BAD_REQUEST

            cart = db.query(Cart).filter_by(user_id=current_user.id).first()
            if not cart:
                return {"message": "Cart not found"}, HTTPStatus.NOT_FOUND

            if not cart.items:
                return {"message": "Cart is empty"}, HTTPStatus.BAD_REQUEST

            # Calculate total amount
            total_amount = (
                db.query(func.sum(Book.price * CartItem.quantity))
                .join(CartItem, Book.id == CartItem.book_id)
                .filter(CartItem.cart_id == cart.id)
                .scalar()
                or 0.0
            )

            # Create order
            order = Order(
                user_id=current_user.id,
                status=OrderStatus.PENDING,
                total_amount=total_amount,
                shipping_address=request.json["shipping_address"],
            )
            db.add(order)
            db.flush()  # Get order ID

            # Create order items from cart items
            for cart_item in cart.items:
                book = db.query(Book).get(cart_item.book_id)
                if book:  # Add check to prevent None access
                    order_item = OrderItem(
                        order_id=order.id, book_id=cart_item.book_id, quantity=cart_item.quantity, price=book.price
                    )
                    db.add(order_item)

            # Clear the cart
            db.query(CartItem).filter_by(cart_id=cart.id).delete()

            db.commit()
            return {"message": "Order created successfully", "order_id": order.id}, HTTPStatus.CREATED


@ns.route("/items/<int:book_id>")
class CartItemResource(Resource):

    @ns.doc("update_cart_item", description="Изменить количество товара в корзине по book_id.")
    @ns.expect(cart_item_update_model)
    @ns.marshal_with(cart_response_model)
    @login_required
    def put(self, book_id):
        """Update cart item quantity"""
        with session_scope() as db:
            data = CartItemCreate(quantity=request.json["quantity"], book_id=book_id)

            cart = db.query(Cart).filter_by(user_id=current_user.id).first()
            if not cart:
                return {"message": "Cart not found"}, HTTPStatus.NOT_FOUND

            cart_item = db.query(CartItem).filter_by(cart_id=cart.id, book_id=book_id).first()

            if not cart_item:
                return {"message": "Item not found in cart"}, HTTPStatus.NOT_FOUND

            cart_item.quantity = data.quantity
            db.commit()
            return get_cart_response()

    @ns.doc("remove_from_cart", description="Удалить товар из корзины по book_id.")
    @ns.marshal_with(cart_response_model)
    @login_required
    def delete(self, book_id):
        """Remove item from cart"""
        with session_scope() as db:
            cart = db.query(Cart).filter_by(user_id=current_user.id).first()
            if not cart:
                return {"message": "Cart not found"}, HTTPStatus.NOT_FOUND

            cart_item = db.query(CartItem).filter_by(cart_id=cart.id, book_id=book_id).first()

            if not cart_item:
                return {"message": "Item not found in cart"}, HTTPStatus.NOT_FOUND

            db.delete(cart_item)
            db.commit()
            return get_cart_response()
