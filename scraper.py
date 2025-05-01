import requests
from bs4 import BeautifulSoup

class Scraper:
    def __init__(self, base_url="https://letterboxd.com"):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0"
        }

    def get(self, url):
        """Fetch HTML content from the provided URL."""
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.text

    def fetch_films_with_ratings(self, path):
        """
        Fetch film titles and ratings from a Letterboxd page.
        
        Args:
            path (str): The URL path (e.g., 'bcentner/films/').

        Returns:
            list[dict]: A list of films with 'title' and 'rating'.
        """
        html = self.get(f"{self.base_url}/{path}")
        soup = BeautifulSoup(html, "html.parser")
        film_items = soup.select("li.poster-container")

        films = []
        for item in film_items:
            img = item.find("img", alt=True)
            title = img["alt"] if img and "alt" in img.attrs else "Unknown Title"
            title = title.title()  # ← THIS is the key fix — call the method with ()
            rating_tag = item.select_one("p.poster-viewingdata span.rating")
            rating = rating_tag.text.strip() if rating_tag else "No rating"
            films.append({"title": title, "rating": rating})

        return films
