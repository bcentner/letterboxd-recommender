from flask import Flask, render_template, request
from scraper import Scraper

app = Flask(__name__)
scraper = Scraper()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        try:
            stats = scraper.fetch_user_stats(username)
            return render_template("results.html", username=username, stats=stats)
        except Exception as e:
            return render_template("error.html", error=str(e))
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
