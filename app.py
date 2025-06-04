from flask import Flask, render_template, request
from scraper import Scraper, FilmDataOptions
from stats import StatsCalculator, UserProfile
from recommendation import MovieRecommendationEngine
import asyncio
import os

app = Flask(__name__)
scraper = Scraper()
stats_calculator = StatsCalculator()

# Optional TMDB API key for enhanced recommendations
tmdb_api_key = os.environ.get('TMDB_API_KEY')
recommendation_engine = MovieRecommendationEngine(tmdb_api_key=tmdb_api_key)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        num_recommendations = int(request.form.get("num_recommendations", 15))
        
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
            
            # Generate recommendations
            print(f"Generating recommendations for {username}")
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
                                 options=options)
                                 
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()
            return render_template("error.html", error=str(e))
            
    return render_template("index.html")

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

if __name__ == "__main__":
    app.run(debug=True)
