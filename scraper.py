import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime
import re
import time
import asyncio
import aiohttp
import json

class Scraper:
    def __init__(self, base_url="https://letterboxd.com"):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.session = None

    async def init_session(self):
        """Initialize the aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close_session(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    def get(self, url):
        """Fetch HTML content from the provided URL."""
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.text

    def get_json(self, url):
        """Fetch JSON content from the provided URL."""
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_total_pages(self, soup):
        """Extract the total number of pages from the pagination."""
        # Find the pagination section
        pagination = soup.select_one("div.paginate-pages")
        if not pagination:
            return 1

        # Find all page links
        page_links = pagination.select("a")
        if not page_links:
            return 1

        # Get the highest page number from the links
        max_page = 1
        for link in page_links:
            # Skip "Newer" and "Older" links
            if link.text.strip() in ["Newer", "Older"]:
                continue
                
            try:
                page_num = int(link.text.strip())
                max_page = max(max_page, page_num)
            except ValueError:
                continue

        return max_page

    async def get_film_details(self, film_url, json_url):
        """Fetch additional details for a film from its JSON endpoint."""
        try:
            data = await self.get_json(json_url)
            
            # Get year
            year = "Unknown"
            if "releaseYear" in data:
                year = str(data["releaseYear"])
            
            # Get genres
            genres = []
            if "genres" in data:
                genres = [genre["name"] for genre in data["genres"]]
            
            return {"year": year, "genres": genres}
        except Exception as e:
            print(f"Error fetching film details: {e}")
            return {"year": "Unknown", "genres": []}

    def fetch_user_stats(self, username):
        """
        Fetch comprehensive statistics about a user's film watching habits.
        
        Args:
            username (str): The Letterboxd username.

        Returns:
            dict: A dictionary containing various statistics about the user's film watching habits.
        """
        # Initialize statistics
        stats = {
            "total_films": 0,
            "average_rating": 0,
            "rating_distribution": Counter(),
            "years": Counter(),
            "genres": Counter(),
            "films": []
        }

        total_rating = 0
        rated_films = 0

        # Get the first page to determine total pages
        first_page_url = f"{self.base_url}/{username}/films/"
        html = self.get(first_page_url)
        soup = BeautifulSoup(html, "html.parser")
        total_pages = self.get_total_pages(soup)

        # Process all pages
        for page in range(1, total_pages + 1):
            if page > 1:
                page_url = f"{self.base_url}/{username}/films/page/{page}/"
                html = self.get(page_url)
                soup = BeautifulSoup(html, "html.parser")

            film_items = soup.select("li.poster-container")
            print(f"\nFound {len(film_items)} film items on page {page}")
            
            for item in film_items:
                stats["total_films"] += 1
                
                # Get film title and link
                img = item.find("img", alt=True)
                title = img["alt"] if img and "alt" in img.attrs else "Unknown Title"
                title = title.title()

                # Get film details from JSON endpoint
                film_poster = item.select_one("div.film-poster")
                year = "Unknown"
                genres = []
                
                if film_poster and "data-details-endpoint" in film_poster.attrs:
                    json_url = f"{self.base_url}{film_poster['data-details-endpoint']}"
                    try:
                        film_data = self.get_json(json_url)
                        
                        # Get year
                        if "releaseYear" in film_data:
                            year = str(film_data["releaseYear"])
                            stats["years"][year] += 1
                        
                        # Get genres
                        if "genres" in film_data:
                            for genre in film_data["genres"]:
                                if "name" in genre:
                                    genres.append(genre["name"])
                                    stats["genres"][genre["name"]] += 1
                        
                        # Add a small delay to be nice to the server
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"Error fetching film details for {title}: {e}")

                # Get rating - looking for the rating in the format "★★★½"
                rating_tag = item.select_one("span.rating")
                rating = None
                if rating_tag:
                    rating_text = rating_tag.text.strip()
                    # Convert star rating to number (e.g., "★★★½" -> "3.5")
                    stars = rating_text.count("★")
                    half_star = "½" in rating_text
                    rating = str(stars + 0.5 if half_star else stars)
                
                if rating:
                    try:
                        rating_float = float(rating)
                        total_rating += rating_float
                        rated_films += 1
                        stats["rating_distribution"][rating] += 1
                    except ValueError:
                        pass

                stats["films"].append({
                    "title": title,
                    "rating": rating,
                    "year": year
                })

        # Calculate average rating
        if rated_films > 0:
            stats["average_rating"] = round(total_rating / rated_films, 2)

        # Get most common genres
        stats["top_genres"] = dict(stats["genres"].most_common(5))
        
        # Get most watched years
        stats["top_years"] = dict(stats["years"].most_common(5))

        # Debug prints
        print("\nFinal Statistics:")
        print("Total films:", stats["total_films"])
        print("Years found:", dict(stats["years"]))
        print("Genres found:", dict(stats["genres"]))
        print("Top genres:", stats["top_genres"])
        print("Top years:", stats["top_years"])

        return stats

    def fetch_user_stats_sync(self, username):
        """Synchronous wrapper for fetch_user_stats."""
        return asyncio.run(self.fetch_user_stats(username))
