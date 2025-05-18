from extensions import app, db, login_manager

# Import models
from models import User, Continent, Country, Dish, Rating, Favorite

# Import initialization function
from init_db import initialize_database

# Import routes
from routes import *

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        initialize_database(db, User, Continent)
    app.run(debug=True)
