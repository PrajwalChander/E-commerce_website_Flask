from flask import Flask, render_template, redirect, request, flash, session
from functools import wraps
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Connect to the database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="project2"  # Update the database name
)
cursor = db.cursor()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Unauthorized access. Please log in.', 'error')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM clients WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        if user:
            session['logged_in'] = True
            session['user_id'] =user[0]  # Assuming the user ID is in the first column
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            error_message = 'Invalid username or password'
            flash(error_message, 'error')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor.execute("SELECT * FROM clients WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            error_message = 'Username already exists. Please create a new one.'
            flash(error_message, 'error')
            return redirect('/register')

        cursor.execute("SELECT * FROM clients WHERE email = %s", (email,))
        existing_email = cursor.fetchone()

        if existing_email:
            error_message = 'Email already exists. Please use a different email.'
            flash(error_message, 'error')
            return redirect('/register')

        cursor.execute("INSERT INTO clients (username, password, email) VALUES (%s, %s, %s)",
                       (username, password, email))
        db.commit()

        flash('Registration successful!', 'success')
        return redirect('/login')
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    # Retrieve all products from the database
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("dashboard.html", products=products)


@app.route('/product/create', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']

        # Get the current user's ID from the session
        user_id = session['user_id']

        cursor.execute("INSERT INTO products (name, description, price, category, user_id) VALUES (%s, %s, %s, %s, %s)",
                       (name, description, price, category, user_id))
        db.commit()
        flash('Product created successfully!', 'success')
        return redirect('/dashboard')

    return render_template('create_product.html')


@app.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']

        # Check if the product exists and belongs to the current user
        cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (product_id, session['user_id']))
        product = cursor.fetchone()

        if product:
            cursor.execute("UPDATE products SET name = %s, description = %s, price = %s, category = %s WHERE id = %s",
                           (name, description, price, category, product_id))
            db.commit()
            flash('Product updated successfully!', 'success')
        else:
            flash('Unauthorized access. You can only edit your own products.', 'error')

        return redirect('/dashboard')

    # Retrieve the product details for editing
    cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (product_id, session['user_id']))
    product = cursor.fetchone()
    if product is None:
        flash('Unauthorized access. You can only edit your own products.', 'error')
        return redirect('/dashboard')

    return render_template('edit_product.html', product=product)


@app.route('/product/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    # Check if the product exists and belongs to the current user
    cursor.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (product_id, session['user_id']))
    product = cursor.fetchone()

    if product:
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        db.commit()
        flash('Product deleted successfully!', 'success')
    else:
        flash('Unauthorized access. You can only delete your own products.', 'error')

    return redirect('/dashboard')

@app.route('/add-to-cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    # Check if the product exists
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    if product:
        # Get the user ID from the session
        user_id = session['user_id']

        # Check if the product is already in the user's cart
        cursor.execute("SELECT * FROM cart WHERE product_id = %s AND user_id = %s", (product_id, user_id))
        cart_item = cursor.fetchone()

        if cart_item:
            flash('Product is already in your cart!', 'info')
        else:
            # Add the product to the cart
            cursor.execute("INSERT INTO cart (product_id, user_id) VALUES (%s, %s)", (product_id, user_id))
            db.commit()
            flash('Product added to cart successfully!', 'success')
    else:
        flash('Product not found!', 'error')

    return redirect('/dashboard')



@app.route('/cart')
@login_required
def view_cart():
    user_id = session['user_id']

    # Fetch the cart items for the current user from the database
    cursor.execute("""
        SELECT cart.cart_id, products.name, products.price, cart.quantity, (products.price * cart.quantity) AS total
        FROM cart
        INNER JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))
    cart_items = cursor.fetchall()

    # Calculate the total value of the cart
    total_value = sum(item[4] for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, total_value=total_value)




@app.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    cart_id = request.form['cart_id']
    quantity = request.form['quantity']

    # Update the quantity in the cart table
    cursor.execute("UPDATE cart SET quantity = %s WHERE cart_id = %s", (quantity, cart_id))
    db.commit()

    flash('Cart updated!', 'success')
    return redirect('/cart')


@app.route('/remove-from-cart/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    # Delete the item from the cart table
    cursor.execute("DELETE FROM cart WHERE cart_id = %s", (cart_id,))
    db.commit()

    flash('Item removed from cart!', 'success')
    return redirect('/cart')


# ...


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
