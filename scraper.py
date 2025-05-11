import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime
import re
import time
import asyncio
import aiohttp
import json
from cache import Cache

class Scraper:
    def __init__(self, base_url="https://letterboxd.com"):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.cache = Cache()
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout

    def __del__(self):
        """Cleanup when the scraper is destroyed."""
        if self.cache:
            self.cache.close()

    async def get_film_details(self, session, film_url, json_url):
        """Fetch additional details for a film from its JSON endpoint or cache."""
        # Extract film ID from the URL for caching
        # Example URL: https://letterboxd.com/film/dont-worry-darling/json/
        film_id = json_url.split('/film/')[-1].split('/')[0]
        
        # Try to get from cache first
        cached_data = self.cache.get_film(film_id)
        if cached_data:
            print(f"Cache hit for film {film_id}")
            return cached_data

        print(f"Cache miss for film {film_id}")
        try:
            async with session.get(json_url) as response:
                # Handle text/json mimetype
                text = await response.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON for {film_id}: {e}")
                    return {"year": "Unknown", "genres": [], "title": "Unknown Title"}
            
            # Get year
            year = "Unknown"
            if "releaseYear" in data:
                year = str(data["releaseYear"])
            
            # Get genres
            genres = []
            if "genres" in data:
                genres = [genre["name"] for genre in data["genres"]]
            
            film_data = {
                "year": year,
                "genres": genres,
                "title": data.get("name", "Unknown Title"),
                "director": data.get("director", "Unknown"),
                "runtime": data.get("runtime", 0),
                "overview": data.get("overview", ""),
                "poster_url": data.get("poster", {}).get("sizes", [{}])[0].get("url", "")
            }
            
            # Cache the film data
            self.cache.set_film(film_id, film_data)
            print(f"Cached film {film_id}")
            
            return film_data
        except Exception as e:
            print(f"Error fetching film details for {film_id}: {e}")
            return {"year": "Unknown", "genres": [], "title": "Unknown Title"}

    async def fetch_user_stats(self, username):
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

        # Create a new session for this request
        async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
            try:
                # Get the first page to determine total pages
                first_page_url = f"{self.base_url}/{username}/films/"
                async with session.get(first_page_url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    total_pages = self.get_total_pages(soup)

                # Process all pages
                for page in range(1, total_pages + 1):
                    if page > 1:
                        page_url = f"{self.base_url}/{username}/films/page/{page}/"
                        async with session.get(page_url) as response:
                            html = await response.text()
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
                        film_data = None
                        
                        if film_poster and "data-details-endpoint" in film_poster.attrs:
                            json_url = f"{self.base_url}{film_poster['data-details-endpoint']}"
                            film_data = await self.get_film_details(session, None, json_url)
                        
                        if film_data:
                            year = film_data.get("year", "Unknown")
                            genres = film_data.get("genres", [])
                            
                            if year != "Unknown":
                                stats["years"][year] += 1
                            
                            for genre in genres:
                                stats["genres"][genre] += 1
                        else:
                            year = "Unknown"
                            genres = []

                        # Get rating
                        rating_tag = item.select_one("span.rating")
                        rating = None
                        if rating_tag:
                            rating_text = rating_tag.text.strip()
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

                        # Add film to the list with all available details
                        film_entry = {
                            "title": film_data.get("title", title) if film_data else title,
                            "rating": rating,
                            "year": year,
                            "genres": genres,
                            "director": film_data.get("director", "Unknown") if film_data else "Unknown",
                            "runtime": film_data.get("runtime", 0) if film_data else 0,
                            "overview": film_data.get("overview", "") if film_data else "",
                            "poster_url": film_data.get("poster_url", "") if film_data else ""
                        }
                        stats["films"].append(film_entry)

                # Calculate average rating
                if rated_films > 0:
                    stats["average_rating"] = round(total_rating / rated_films, 2)

                # Get most common genres and years
                stats["top_genres"] = dict(stats["genres"].most_common(5))
                stats["top_years"] = dict(stats["years"].most_common(5))
                
                return stats

            except Exception as e:
                print(f"Error in fetch_user_stats: {e}")
                raise
            finally:
                # Clear expired entries periodically
                self.cache.clear_expired()

    def fetch_user_stats_sync(self, username):
        """Synchronous wrapper for fetch_user_stats."""
        try:
            # Create a new event loop for this request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.fetch_user_stats(username))
            finally:
                # Clean up the event loop
                loop.close()
        except Exception as e:
            print(f"Error in fetch_user_stats_sync: {e}")
            raise

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
