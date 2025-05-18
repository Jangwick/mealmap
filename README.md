# MealMap - Traditional Food Discovery App

MealMap is a web application that helps users discover traditional foods from around the world. Users can browse foods by region, search for specific dishes, and save their favorites.

## Features

- **Browse by Region**: Explore traditional foods by continent and country
- **Search Functionality**: Find dishes by name or region
- **User Authentication**: Register, login, and maintain a profile
- **Admin Dashboard**: Manage dishes, countries, and user content
- **Dish Information**: Detailed information about each traditional dish
- **Interactive Ratings**: Leave ratings and comments on dishes
- **Favorite System**: Save dishes to a personal favorites list

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```

## Default Admin Access

- Username: admin
- Password: admin123

## Technology Stack

- Backend: Python + Flask
- Database: SQLite with SQLAlchemy ORM
- Frontend: HTML, CSS, JavaScript, Bootstrap 5
- Authentication: Flask-Login

## Project Structure

- `/templates` - HTML templates
- `/static` - CSS, JavaScript, and uploaded images
- `/models.py` - Database models
- `/routes.py` - Application routes and controllers
- `/app.py` - Application initialization
