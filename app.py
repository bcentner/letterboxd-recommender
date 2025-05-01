from flask import Flask, render_template, request
from scraper import Scraper

app = Flask(__name__)
scraper = Scraper()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        try:
            films = scraper.fetch_films_with_ratings(username)
            return render_template("results.html", username=username, films=films)
        except Exception as e:
            return f"Error fetching films: {e}", 500
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
