from flask import Flask, render_template, request
from scraper import Scraper, FilmDataOptions
from stats import StatsCalculator
from recommendation import MovieRecommendationEngine
import os
import json
import signal
import sys
import atexit

app = Flask(__name__)
scraper = Scraper()
stats_calculator = StatsCalculator()

# Optional env variables
tmdb_api_key = os.environ.get('TMDB_API_KEY')
movie_db_path = os.environ.get('MOVIE_DATABASE_PATH', 'movie_database.json')

# Initialize recommendation engine with our movie database
recommendation_engine = MovieRecommendationEngine(tmdb_api_key=tmdb_api_key, movie_db_file=movie_db_path)

# Get database stats for display
db_stats = recommendation_engine.get_database_stats()
print(f"Movie Database Stats: {db_stats}")
print(f"Using movie database: {movie_db_path}")

def cleanup():
    """Cleanup function to properly close cache and other resources"""
    try:
        if hasattr(scraper, 'cache') and scraper.cache:
            scraper.cache.close()
        print("Cleanup completed successfully")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

atexit.register(cleanup)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        # Always use 5 recommendations
        num_recommendations = 5
        
        # Get data fetching options from form
        options = FilmDataOptions(
            basic_info=True,  # Always fetch basic info for recommendations
            genres=request.form.get("fetch_genres") == "on",
            cast=request.form.get("fetch_cast") == "on",
            ratings=request.form.get("fetch_ratings") == "on"
        )
        
        try:
            # Fetch user stats and watched films
            print(f"Fetching data for user: {username}")
            stats = scraper.fetch_user_stats_sync(username, options)
            watched_films = scraper.get_watched_films_sync(username)
            
            # Calculate user profile
            user_profile = stats_calculator.calculate_user_profile(stats)
            user_profile.username = username
            user_profile.watched_films = watched_films
            
            # Generate recommendations using our movie database
            print(f"Generating recommendations for {username} using movie database")
            recommendations = recommendation_engine.generate_recommendations(
                user_profile, num_recommendations
            )
            
            # Calculate additional insights
            rating_tendency = stats_calculator.calculate_rating_tendency(user_profile.rating_distribution)
            preferred_genres = stats_calculator.identify_genre_preferences(user_profile.preferred_genres)
            preferred_directors = stats_calculator.identify_director_preferences(user_profile.preferred_directors)
            
            return render_template("recommendations.html", 
                                 username=username,
                                 user_profile=user_profile,
                                 recommendations=recommendations,
                                 rating_tendency=rating_tendency,
                                 preferred_genres=preferred_genres,
                                 preferred_directors=preferred_directors,
                                 stats=stats,
                                 options=options,
                                 db_stats=db_stats)
                                 
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()
            return render_template("error.html", error=str(e))
    
    # Pass database stats to the index page
    return render_template("index.html", db_stats=db_stats)

@app.route("/stats/<username>")
def view_stats(username):
    """Optional endpoint to view just stats (original functionality)"""
    options = FilmDataOptions(basic_info=True, genres=True, cast=False, ratings=True)
    
    try:
        stats = scraper.fetch_user_stats_sync(username, options)
        return render_template("results.html", username=username, stats=stats, options=options)
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return render_template("error.html", error=str(e))

@app.route("/database")
def database_info():
    """Show information about the movie database"""
    return render_template("database.html", db_stats=db_stats)

def load_movies_from_db():
    global app_movies
    try:
        # Read (or merge) the database (movie_database.json) into the in-memory cache (app_movies) so that if the crawler (or another process) updates the database (for example, by merging in new movies) the app will load (or merge) the updated (or merged) database.
        if os.path.exists(DATABASE_FILE):
             with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                 db_movies = json.load(f)
                 # Merge (or overwrite) the in-memory cache (app_movies) with the database (db_movies) (using imdb_id as the key) so that if the crawler (or another process) updates (or merges) the database (for example, by merging in new movies) the app will load (or merge) the updated (or merged) database.
                 db_dict = { m["imdb_id"]: m for m in db_movies }
                 for m in app_movies:
                     if m["imdb_id"] in db_dict:
                         db_dict[m["imdb_id"]] = m
                 app_movies = list(db_dict.values())
                 print(f"Loaded (merged) {len(app_movies)} movies from database (file: {DATABASE_FILE})")
        else:
             print(f"Database file ({DATABASE_FILE}) does not exist (or is empty). (No movies loaded.)")
             app_movies = []
    except Exception as e:
         print(f"Error (or exception) loading (or merging) movies from database: {e} (file may not exist or be empty.)")
         app_movies = []

class PrefixMiddleware:
    def __init__(self, app, prefix='/letterboxd-recommender'):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        print("PrefixMiddleware called with PATH_INFO:", environ.get('PATH_INFO'))
        if environ.get('PATH_INFO', '').startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
        return self.app(environ, start_response)

application = PrefixMiddleware(app)

if __name__ == "__main__":
    try:
        print("Starting Letterboxd Recommender...")
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cleanup()
