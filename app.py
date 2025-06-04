from flask import Flask, render_template, request
from scraper import Scraper, FilmDataOptions
import asyncio

app = Flask(__name__)
scraper = Scraper()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        
        # Get data fetching options from form
        options = FilmDataOptions(
            basic_info=request.form.get("fetch_basic") == "on",
            genres=request.form.get("fetch_genres") == "on",
            cast=request.form.get("fetch_cast") == "on",
            ratings=request.form.get("fetch_ratings") == "on"
        )
        
        try:
            stats = scraper.fetch_user_stats_sync(username, options)
            return render_template("results.html", username=username, stats=stats, options=options)
        except Exception as e:
            print(f"Error fetching user stats: {e}")
            return render_template("error.html", error=str(e))
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
