from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import functools

# Import from extensions instead of app
from extensions import app, db, login_manager
from models import User, Continent, Country, Dish, Rating, Favorite

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    continents = Continent.query.all()
    latest_dishes = Dish.query.order_by(Dish.created_at.desc()).limit(6).all()
    
    # Get highest rated dishes for featured section
    featured_dishes = db.session.query(
        Dish, db.func.avg(Rating.rating).label('avg_rating')
    ).join(Rating).group_by(Dish.id).order_by(db.desc('avg_rating')).limit(3).all()
    
    # Get most favorited dishes
    popular_dishes = db.session.query(
        Dish, db.func.count(Favorite.id).label('fav_count')
    ).join(Favorite).group_by(Dish.id).order_by(db.desc('fav_count')).limit(3).all()
    
    return render_template('index.html', 
                          continents=continents, 
                          latest_dishes=latest_dishes, 
                          featured_dishes=featured_dishes,
                          popular_dishes=popular_dishes)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
            
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
            
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('login'))
            
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        
        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(next_page or url_for('index'))
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    favorite_dishes = [favorite.dish for favorite in favorites]
    
    # Get user ratings
    user_ratings = Rating.query.filter_by(user_id=current_user.id).order_by(Rating.created_at.desc()).all()
    
    # Handle profile updates
    if request.method == 'POST':
        if 'update_profile' in request.form:
            # Process profile update
            email = request.form.get('email')
            current_password = request.form.get('current_password')
            
            # Verify current password
            if check_password_hash(current_user.password_hash, current_password):
                # Update email if changed
                if email != current_user.email:
                    existing_email = User.query.filter_by(email=email).first()
                    if existing_email:
                        flash('Email already in use.', 'danger')
                    else:
                        current_user.email = email
                        db.session.commit()
                        flash('Profile updated successfully!', 'success')
                
                # Update password if provided
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                if new_password:
                    if new_password == confirm_password:
                        current_user.password_hash = generate_password_hash(new_password)
                        db.session.commit()
                        flash('Password updated successfully!', 'success')
                    else:
                        flash('New passwords do not match.', 'danger')
            else:
                flash('Current password is incorrect.', 'danger')
    
    return render_template('profile.html', 
                          favorite_dishes=favorite_dishes, 
                          user_ratings=user_ratings)

@app.route('/browse/<continent_name>')
def browse_continent(continent_name):
    continent = Continent.query.filter_by(name=continent_name).first_or_404()
    countries = Country.query.filter_by(continent_id=continent.id).all()
    return render_template('browse_continent.html', continent=continent, countries=countries)

@app.route('/browse/country/<country_name>')
def browse_country(country_name):
    country = Country.query.filter_by(name=country_name).first_or_404()
    dishes = Dish.query.filter_by(country_id=country.id).all()
    return render_template('browse_country.html', country=country, dishes=dishes)

@app.route('/map')
def food_map():
    # Get all continents with countries
    continents = Continent.query.all()
    
    # Count dishes per country for the map
    country_stats = db.session.query(
        Country.name, 
        Country.id,
        db.func.count(Dish.id).label('dish_count')
    ).outerjoin(Dish).group_by(Country.id).all()
    
    # Format data for the map
    map_data = {}
    for continent in continents:
        map_data[continent.name] = {
            "id": continent.id,
            "countries": []
        }
        
        for country in continent.countries:
            country_data = {
                "id": country.id,
                "name": country.name,
                "dish_count": 0
            }
            
            # Find matching stat if exists
            for stat in country_stats:
                if stat[1] == country.id:
                    country_data["dish_count"] = stat[2]
                    break
                    
            map_data[continent.name]["countries"].append(country_data)
    
    return render_template('food_map.html', 
                          continents=continents,
                          map_data=map_data)

@app.route('/search')
def search():
    query = request.args.get('query', '')
    cuisine_filter = request.args.get('cuisine', '')
    dietary_filter = request.args.get('dietary', '')
    
    if not query and not cuisine_filter:
        return render_template('search.html', dishes=[], query='')
    
    # Base query for dishes
    dish_query = Dish.query
    
    # Apply text search filter if provided
    if query:
        dish_query = dish_query.filter(Dish.name.ilike(f'%{query}%') | 
                                      Dish.description.ilike(f'%{query}%'))
    
    # Apply cuisine filter if provided
    if cuisine_filter:
        country = Country.query.filter_by(name=cuisine_filter).first()
        if country:
            dish_query = dish_query.filter(Dish.country_id == country.id)
    
    # Apply dietary filter - (Note: We'd need to add dietary_tags to Dish model)
    # This is a placeholder - you would need to implement the dietary tags feature
    # if dietary_filter:
    #     dish_query = dish_query.filter(Dish.dietary_tags.contains(dietary_filter))
    
    dishes = dish_query.all()
    
    # Get all countries for the filter dropdown
    countries = Country.query.order_by(Country.name).all()
    
    return render_template('search.html', 
                          dishes=dishes, 
                          query=query, 
                          countries=countries,
                          selected_country=cuisine_filter)

@app.route('/dish/<int:dish_id>/share', methods=['GET'])
def share_dish(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    
    # Generate share links for social media
    share_url = request.host_url + url_for('dish_detail', dish_id=dish.id)[1:]
    share_title = f"Check out {dish.name} on MealMap!"
    share_text = f"I discovered {dish.name} from {dish.country.name} on MealMap. Take a look!"
    
    twitter_url = f"https://twitter.com/intent/tweet?text={share_text}&url={share_url}"
    facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={share_url}"
    whatsapp_url = f"https://wa.me/?text={share_text} {share_url}"
    
    return jsonify({
        'dish_name': dish.name,
        'share_url': share_url,
        'twitter_url': twitter_url,
        'facebook_url': facebook_url,
        'whatsapp_url': whatsapp_url
    })

@app.route('/dish/<int:dish_id>', methods=['GET'])
def dish_detail(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    ratings = Rating.query.filter_by(dish_id=dish_id).order_by(Rating.created_at.desc()).all()
    
    avg_rating = 0
    if ratings:
        avg_rating = sum(r.rating for r in ratings) / len(ratings)
    
    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(user_id=current_user.id, dish_id=dish_id).first() is not None
    
    # Get similar dishes (from same country)
    similar_dishes = Dish.query.filter(
        Dish.country_id == dish.country_id,
        Dish.id != dish.id
    ).limit(3).all()
    
    # Check if the dish was added/edited by admin (for admin connection)
    admin_edit = False
    if dish.updated_at and dish.updated_at > dish.created_at:
        admin_edit = True
    
    return render_template('dish_detail.html', 
                          dish=dish, 
                          ratings=ratings, 
                          avg_rating=avg_rating, 
                          is_favorite=is_favorite,
                          similar_dishes=similar_dishes,
                          admin_edit=admin_edit)

@app.route('/rate/<int:dish_id>', methods=['POST'])
@login_required
def rate_dish(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    
    # Check if user already rated this dish
    existing_rating = Rating.query.filter_by(user_id=current_user.id, dish_id=dish_id).first()
    
    rating_value = int(request.form.get('rating'))
    comment = request.form.get('comment', '')
    
    if existing_rating:
        existing_rating.rating = rating_value
        existing_rating.comment = comment
    else:
        new_rating = Rating(
            user_id=current_user.id,
            dish_id=dish_id,
            rating=rating_value,
            comment=comment
        )
        db.session.add(new_rating)
        
    db.session.commit()
    flash('Your rating has been submitted!', 'success')
    return redirect(url_for('dish_detail', dish_id=dish_id))

@app.route('/favorite/<int:dish_id>', methods=['POST'])
@login_required
def toggle_favorite(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    
    favorite = Favorite.query.filter_by(user_id=current_user.id, dish_id=dish_id).first()
    
    if favorite:
        db.session.delete(favorite)
        message = 'Removed from favorites'
    else:
        new_favorite = Favorite(user_id=current_user.id, dish_id=dish_id)
        db.session.add(new_favorite)
        message = 'Added to favorites'
        
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'message': message})
    
    flash(message, 'success')
    return redirect(url_for('dish_detail', dish_id=dish_id))

# Admin routes
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    dishes_count = Dish.query.count()
    countries_count = Country.query.count()
    users_count = User.query.count()
    
    # Get recent activities (dishes, ratings, etc.)
    recent_dishes = Dish.query.order_by(Dish.created_at.desc()).limit(5).all()
    recent_ratings = Rating.query.order_by(Rating.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         dishes_count=dishes_count,
                         countries_count=countries_count,
                         users_count=users_count,
                         recent_dishes=recent_dishes,
                         recent_ratings=recent_ratings)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/activity')
@login_required
@admin_required
def admin_user_activity():
    # Get recent user activities (ratings, favorites)
    recent_ratings = Rating.query.order_by(Rating.created_at.desc()).limit(20).all()
    recent_favorites = Favorite.query.order_by(Favorite.created_at.desc()).limit(20).all()
    
    return render_template('admin/user_activity.html', 
                          ratings=recent_ratings, 
                          favorites=recent_favorites)

@app.route('/admin/analytics/overview')
@login_required
@admin_required
def admin_analytics_overview():
    # Basic analytics data
    total_users = User.query.count()
    total_dishes = Dish.query.count()
    total_ratings = Rating.query.count()
    total_favorites = Favorite.query.count()
    
    # Countries with most dishes
    top_countries = db.session.query(
        Country.name, db.func.count(Dish.id).label('dish_count')
    ).join(Dish).group_by(Country.id).order_by(db.desc('dish_count')).limit(5).all()
    
    return render_template('admin/analytics_overview.html',
                          total_users=total_users,
                          total_dishes=total_dishes,
                          total_ratings=total_ratings,
                          total_favorites=total_favorites,
                          top_countries=top_countries)

@app.route('/admin/analytics/users')
@login_required
@admin_required
def admin_analytics_users():
    return render_template('admin/analytics_users.html')

@app.route('/admin/analytics/content')
@login_required
@admin_required
def admin_analytics_content():
    # Get dishes with highest ratings
    top_rated_dishes = db.session.query(
        Dish, db.func.avg(Rating.rating).label('avg_rating'), db.func.count(Rating.id).label('rating_count')
    ).join(Rating).group_by(Dish.id).having(db.func.count(Rating.id) > 0).order_by(db.desc('avg_rating')).limit(10).all()
    
    # Get most favorited dishes
    most_favorited = db.session.query(
        Dish, db.func.count(Favorite.id).label('favorite_count')
    ).join(Favorite).group_by(Dish.id).order_by(db.desc('favorite_count')).limit(10).all()
    
    return render_template('admin/analytics_content.html',
                          top_rated_dishes=top_rated_dishes,
                          most_favorited=most_favorited)

@app.route('/admin/settings')
@login_required
@admin_required
def admin_settings():
    return render_template('admin/settings.html')

@app.route('/admin/search')
@login_required
@admin_required
def admin_search():
    query = request.args.get('query', '')
    search_type = request.args.get('type', 'dish')
    
    results = []
    if query:
        if search_type == 'dish':
            results = Dish.query.filter(Dish.name.ilike(f'%{query}%')).all()
        elif search_type == 'country':
            results = Country.query.filter(Country.name.ilike(f'%{query}%')).all()
        elif search_type == 'user':
            results = User.query.filter(User.username.ilike(f'%{query}%')).all()
    
    return render_template('admin/search_results.html', 
                          query=query,
                          search_type=search_type,
                          results=results)

@app.route('/admin/dishes')
@login_required
@admin_required
def admin_dishes():
    dishes = Dish.query.all()
    return render_template('admin/dishes.html', dishes=dishes)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/admin/dishes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_dish():
    countries = Country.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        country_id = request.form.get('country_id')
        
        # Validation
        if not name or not description or not country_id:
            flash('All fields are required!', 'danger')
            return redirect(url_for('add_dish'))
            
        image_path = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Generate unique filename
                filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = f"uploads/{filename}"
        
        new_dish = Dish(
            name=name,
            description=description,
            country_id=country_id,
            image_path=image_path
        )
        
        db.session.add(new_dish)
        db.session.commit()
        
        flash('New dish added successfully!', 'success')
        return redirect(url_for('admin_dishes'))
        
    return render_template('admin/add_dish.html', countries=countries)

@app.route('/admin/dishes/edit/<int:dish_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_dish(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    countries = Country.query.all()
    
    if request.method == 'POST':
        dish.name = request.form.get('name')
        dish.description = request.form.get('description')
        dish.country_id = request.form.get('country_id')
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Remove old image if exists
                if dish.image_path:
                    old_image_path = os.path.join(app.root_path, 'static', dish.image_path)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                dish.image_path = f"uploads/{filename}"
        
        db.session.commit()
        flash('Dish updated successfully!', 'success')
        return redirect(url_for('admin_dishes'))
        
    return render_template('admin/edit_dish.html', dish=dish, countries=countries)

@app.route('/admin/dishes/delete/<int:dish_id>', methods=['POST'])
@login_required
@admin_required
def delete_dish(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    
    # Delete image file if it exists
    if dish.image_path:
        image_path = os.path.join(app.root_path, 'static', dish.image_path)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    # Delete related ratings and favorites
    Rating.query.filter_by(dish_id=dish_id).delete()
    Favorite.query.filter_by(dish_id=dish_id).delete()
    
    db.session.delete(dish)
    db.session.commit()
    
    flash('Dish deleted successfully!', 'success')
    return redirect(url_for('admin_dishes'))

@app.route('/admin/countries')
@login_required
@admin_required
def admin_countries():
    countries = Country.query.all()
    continents = Continent.query.all()
    return render_template('admin/countries.html', countries=countries, continents=continents)

# Add this new route
@app.route('/admin/countries/delete/<int:country_id>', methods=['POST'])
@login_required
@admin_required
def delete_country(country_id):
    country = Country.query.get_or_404(country_id)
    
    # Check if country has dishes
    has_dishes = Dish.query.filter_by(country_id=country_id).first() is not None
    
    if has_dishes:
        flash('Cannot delete country that has dishes. Remove all dishes from this country first.', 'danger')
        return redirect(url_for('admin_countries'))
    
    country_name = country.name
    db.session.delete(country)
    db.session.commit()
    
    flash(f'Country "{country_name}" deleted successfully!', 'success')
    return redirect(url_for('admin_countries'))

@app.route('/admin/countries/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_country():
    continents = Continent.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        continent_id = request.form.get('continent_id')
        
        if not name or not continent_id:
            flash('All fields are required!', 'danger')
            return redirect(url_for('add_country'))
            
        existing_country = Country.query.filter_by(name=name).first()
        if existing_country:
            flash('Country already exists!', 'danger')
            return redirect(url_for('add_country'))
            
        new_country = Country(name=name, continent_id=continent_id)
        db.session.add(new_country)
        db.session.commit()
        
        flash('Country added successfully!', 'success')
        return redirect(url_for('admin_countries'))
        
    return render_template('admin/add_country.html', continents=continents)

@app.route('/admin/countries/edit/<int:country_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_country(country_id):
    country = Country.query.get_or_404(country_id)
    continents = Continent.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        continent_id = request.form.get('continent_id')
        
        if not name or not continent_id:
            flash('All fields are required!', 'danger')
            return redirect(url_for('edit_country', country_id=country_id))
            
        existing_country = Country.query.filter(Country.name == name, Country.id != country_id).first()
        if existing_country:
            flash('Country name already exists!', 'danger')
            return redirect(url_for('edit_country', country_id=country_id))
            
        country.name = name
        country.continent_id = continent_id
        db.session.commit()
        
        flash('Country updated successfully!', 'success')
        return redirect(url_for('admin_countries'))
        
    return render_template('admin/edit_country.html', country=country, continents=continents)

@app.route('/admin/users/<int:user_id>')
@login_required
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    # Get user's ratings with dish information
    user_ratings = Rating.query.filter_by(user_id=user.id).order_by(Rating.created_at.desc()).all()
    
    # Get user's favorites
    favorites = Favorite.query.filter_by(user_id=user.id).order_by(Favorite.created_at.desc()).all()
    
    # Get creation date and other metadata
    user_joined = user.created_at if hasattr(user, 'created_at') else "Not available"
    
    # Calculate statistics
    stats = {
        'total_ratings': len(user_ratings),
        'avg_rating': sum(r.rating for r in user_ratings) / len(user_ratings) if user_ratings else 0,
        'total_favorites': len(favorites),
        'recent_activity': max([r.created_at for r in user_ratings] + 
                              [f.created_at for f in favorites], default=None) if (user_ratings or favorites) else None
    }
    
    return render_template('admin/user_detail.html', 
                          user=user, 
                          ratings=user_ratings,
                          favorites=favorites,
                          stats=stats,
                          user_joined=user_joined)

# Add these new admin routes for user management

@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Don't allow editing the admin account if there's only one admin
    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1 and 'is_admin' not in request.form:
        flash('Cannot remove admin status from the only administrator.', 'danger')
        return redirect(url_for('admin_user_detail', user_id=user.id))
    
    user.username = request.form.get('username')
    user.email = request.form.get('email')
    user.is_admin = 'is_admin' in request.form
    
    db.session.commit()
    flash('User updated successfully.', 'success')
    return redirect(url_for('admin_user_detail', user_id=user.id))

@app.route('/admin/users/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    
    # Check if trying to reset admin password
    if user.is_admin and current_user.id != user.id:
        flash('For security reasons, admin passwords can only be reset by themselves.', 'danger')
        return redirect(url_for('admin_user_detail', user_id=user.id))
    
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('admin_user_detail', user_id=user.id))
    
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash('Password reset successfully.', 'success')
    return redirect(url_for('admin_user_detail', user_id=user.id))
