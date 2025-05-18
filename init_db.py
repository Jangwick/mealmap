from werkzeug.security import generate_password_hash

def initialize_database(db, User, Continent):
    """Initialize database with default data."""
    # Check if continents exist
    if Continent.query.count() == 0:
        continents = ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania', 'Antarctica']
        for continent_name in continents:
            continent = Continent(name=continent_name)
            db.session.add(continent)
        db.session.commit()
        
    # Create admin user if doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@mealmap.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
