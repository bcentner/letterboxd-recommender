from bs4 import BeautifulSoup
from collections import Counter, defaultdict
from datetime import datetime
import asyncio
import aiohttp
import json
from cache import Cache
from dataclasses import dataclass
from typing import List, Dict, Optional, Set, Tuple, Any
from concurrent.futures import ThreadPoolExecutor

@dataclass
class FilmDataOptions:
    """Options for what film data to fetch"""
    basic_info: bool = True  # title, year, director, runtime, overview, poster
    genres: bool = False     # film genres
    cast: bool = False       # cast information
    ratings: bool = True     # rating information

class Scraper:
    def __init__(self, base_url="https://letterboxd.com"):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.cache = Cache()
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    def __del__(self):
        """Cleanup when the scraper is destroyed."""
        try:
            if hasattr(self, 'cache') and self.cache:
                self.cache.close()
        except:
            pass  # Ignore errors during destruction

    async def _fetch_with_semaphore(self, session, url: str) -> Tuple[str, str]:
        """Fetch URL with rate limiting."""
        try:
            async with self.semaphore:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise RuntimeError(f"HTTP {response.status} for {url}")
                    return url, await response.text()
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            raise 

    async def _fetch_multiple_urls(self, session, urls: List[str]) -> Dict[str, str]:
        """Fetch multiple URLs in parallel."""
        results = {}
        tasks = []
        for url in urls:
            task = asyncio.create_task(self._fetch_with_semaphore(session, url))
            tasks.append(task)
        
        try:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for url, result in zip(urls, completed):
                if isinstance(result, Exception):
                    print(f"Failed to fetch {url}: {str(result)}")
                else:
                    results[url] = result[1]  # result is a tuple of (url, content)
        except Exception as e:
            print(f"Error in _fetch_multiple_urls: {str(e)}")
        
        return results

    async def get_film_data(self, session, film_id: str, film_url: str, json_url: str, options: FilmDataOptions) -> Dict:
        """Fetch all requested film data in parallel."""
        film_data = {}
        urls_to_fetch = []
        cache_keys = []

        cached_basic = self.cache.get_film(film_id, "basic_info")
        if cached_basic:
            film_data.update(cached_basic)
        else:
            urls_to_fetch.append(json_url)
            cache_keys.append(("basic_info", json_url))

        if options.genres:
            cached_genres = self.cache.get_film(film_id, "genres")
            if cached_genres:
                film_data["genres"] = cached_genres
            else:
                genre_url = f"{film_url}genres/"
                urls_to_fetch.append(genre_url)
                cache_keys.append(("genres", genre_url))

        if options.cast:
            cached_cast = self.cache.get_film(film_id, "cast")
            if cached_cast:
                film_data["cast"] = cached_cast
            else:
                urls_to_fetch.append(f"{film_url}crew/")
                cache_keys.append(("cast", f"{film_url}crew/"))


        if urls_to_fetch:
            try:
                responses = await self._fetch_multiple_urls(session, urls_to_fetch)
                
                for data_type, url in cache_keys:
                    if url in responses:
                        content = responses[url]
                        if data_type == "basic_info":
                            try:
                                data = json.loads(content)
                                basic_info = {
                                    "title": data.get("name", "Unknown Title"),
                                    "year": str(data.get("releaseYear", "Unknown")),
                                    "director": data.get("director", "Unknown"),
                                    "runtime": data.get("runtime", 0),
                                    "overview": data.get("overview", ""),
                                    "poster_url": data.get("poster", {}).get("sizes", [{}])[0].get("url", "")
                                }
                                film_data.update(basic_info)
                                self.cache.set_film(film_id, basic_info, "basic_info")
                            except json.JSONDecodeError as e:
                                print(f"Error decoding JSON for {film_id}: {e}")
                                film_data["year"] = "Unknown"
                        
                        elif data_type == "genres":
                            try:
                                soup = BeautifulSoup(content, "html.parser")
                                genres_section = soup.select_one("#tab-genres")
                                if genres_section:
                                    genres = [
                                        a.text.strip()
                                        for p in genres_section.select("p")
                                        for a in p.find_all("a", href=True)
                                        if "genre" in a["href"]    
                                    ]
                                    if genres:
                                        film_data["genres"] = genres
                                        self.cache.set_film(film_id, genres, "genres")
                                else:
                                    print(f"No genres section found for {film_id}")
                            except Exception as e:
                                print(f"Error processing genres for {film_id}: {str(e)}")
                                print(f"Content received: {content[:200]}...")  # Print first 200 chars of content
                        
                        elif data_type == "cast":
                            try:
                                soup = BeautifulSoup(content, "html.parser")
                                cast_list = []
                                cast_section = soup.select_one("#tab-cast")
                                if cast_section:
                                    for cast_item in cast_section.select(".cast-member"):
                                        name = cast_item.select_one(".name")
                                        role = cast_item.select_one(".role")
                                        if name:
                                            cast_list.append({
                                                "name": name.text.strip(),
                                                "role": role.text.strip() if role else "Unknown"
                                            })
                                if cast_list:  
                                    film_data["cast"] = cast_list
                                    self.cache.set_film(film_id, cast_list, "cast")
                            except Exception as e:
                                print(f"Error processing cast for {film_id}: {e}")
            except Exception as e:
                print(f"Error fetching data for film {film_id}: {e}")

        return film_data

    async def fetch_user_stats(self, username: str, options: FilmDataOptions, session: aiohttp.ClientSession) -> Dict:
        """Fetch comprehensive statistics about a user's film watching habits."""
        stats = {
            "total_films": 0,
            "average_rating": 0,
            "rating_distribution": Counter() if options.ratings else None,
            "years": Counter(),
            "genres": Counter() if options.genres else None,
            "directors": Counter(),
            "decades": Counter(),
            "monthly_distribution": Counter(),
        }

        total_rating = 0
        rated_films = 0
        processed_films = 0

        try:
            first_page_url = f"{self.base_url}/{username}/films/"
            first_page_html = await self._fetch_url(session, first_page_url)
            if not first_page_html:
                raise RuntimeError(f"Failed to fetch user profile")
            
            soup = BeautifulSoup(first_page_html, "html.parser")
            total_pages = self.get_total_pages(soup)
            
            # Process each page
            for page in range(1, total_pages + 1):
                page_url = f"{self.base_url}/{username}/films/page/{page}/" if page > 1 else first_page_url
                if page > 1:
                    page_html = await self._fetch_url(session, page_url)
                    if not page_html:
                        print(f"Warning: Failed to fetch page {page}")
                        continue
                    soup = BeautifulSoup(page_html, "html.parser")

                film_items = soup.select("li.poster-container")
                print(f"\nFound {len(film_items)} film items on page {page}")

                # Prepare film data requests
                film_tasks = []
                for item in film_items:
                    stats["total_films"] += 1
                    
                    film_poster = item.select_one("div.film-poster")
                    if not film_poster or "data-details-endpoint" not in film_poster.attrs:
                        print(f"Skipping film without data-details-endpoint on page {page}")
                        continue

                    json_url = f"{self.base_url}{film_poster['data-details-endpoint']}"
                    film_id = json_url.split('/film/')[-1].split('/')[0]
                    film_url = f"{self.base_url}/film/{film_id}/"

                    # Get watch date if available
                    date_tag = item.select_one("time")
                    if date_tag and "datetime" in date_tag.attrs:
                        try:
                            watch_date = datetime.fromisoformat(date_tag["datetime"].replace("Z", "+00:00"))
                            stats["monthly_distribution"][watch_date.strftime("%Y-%m")] += 1
                        except ValueError:
                            pass

                    # Add film data task
                    film_tasks.append((item, self.get_film_data(session, film_id, film_url, json_url, options)))

                # Process film data in parallel
                for item, film_task in film_tasks:
                    try:
                        film_data = await film_task
                        processed_films += 1
                        
                        if "year" in film_data:
                            try:
                                year = int(film_data["year"])
                                stats["years"][year] += 1
                                decade = (year // 10) * 10
                                stats["decades"][f"{decade}s"] += 1
                            except (ValueError, TypeError):
                                print(f"Invalid year value for film: {film_data.get('title', 'Unknown')}")

                        if "director" in film_data and film_data["director"] != "Unknown":
                            stats["directors"][film_data["director"]] += 1
                        
                        if options.genres and "genres" in film_data and film_data["genres"]:
                            for genre in film_data["genres"]:
                                stats["genres"][genre] += 1

                        if options.ratings:
                            rating = await self.get_film_rating(item)
                            if rating:
                                try:
                                    rating_float = float(rating)
                                    total_rating += rating_float
                                    rated_films += 1
                                    stats["rating_distribution"][rating] += 1
                                except ValueError:
                                    pass

                    except Exception as e:
                        print(f"Error processing film: {str(e)}")

            print(f"\nProcessed {processed_films} films out of {stats['total_films']} total films")
            print(f"Genres counter: {stats['genres']}")

            if options.ratings and rated_films > 0:
                stats["average_rating"] = round(total_rating / rated_films, 2)

            if options.genres:
                stats["top_genres"] = dict(stats["genres"].most_common(10))
            stats["top_years"] = dict(stats["years"].most_common(10))
            stats["top_directors"] = dict(stats["directors"].most_common(10))
            stats["top_decades"] = dict(stats["decades"].most_common())
            stats["monthly_watching"] = dict(stats["monthly_distribution"].most_common(12))

            if stats["total_films"] > 0:
                stats["films_per_year"] = round(stats["total_films"] / len(stats["years"]), 2)
                if options.ratings:
                    stats["rating_percentages"] = {
                        rating: round((count / rated_films) * 100, 1)
                        for rating, count in stats["rating_distribution"].items()
                    }

            stats["debug"] = {
                "total_films_found": stats["total_films"],
                "films_processed": processed_films,
                "years_count": len(stats["years"]),
                "genres_count": len(stats["genres"]) if options.genres else 0,
                "ratings_count": rated_films if options.ratings else 0
            }
            
            return stats

        except Exception as e:
            print(f"Error in fetch_user_stats: {e}")
            raise

    async def get_film_rating(self, item) -> Optional[str]:
        """Extract rating from a film item."""
        rating_tag = item.select_one("span.rating")
        if rating_tag:
            rating_text = rating_tag.text.strip()
            stars = rating_text.count("★")
            half_star = "½" in rating_text
            return str(stars + 0.5 if half_star else stars)
        return None

    def fetch_user_stats_sync(self, username: str, options: FilmDataOptions) -> Dict:
        """Synchronous wrapper for fetch_user_stats."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._run_scraper(username, options))
        finally:
            loop.close()

    async def _run_scraper(self, username: str, options: FilmDataOptions) -> Dict:
        """Main entry point for scraping that ensures a single session is used."""
        async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
            return await self.fetch_user_stats(username, options, session)

    async def _fetch_url(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch a single URL with rate limiting."""
        async with self.semaphore:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"HTTP {response.status} for {url}")
                        return None
                    return await response.text()
            except Exception as e:
                print(f"Error fetching {url}: {str(e)}")
                return None

    def get_total_pages(self, soup):
        """Extract the total number of pages from the pagination."""
        pagination = soup.select_one("div.paginate-pages")
        if not pagination:
            return 1

        page_links = pagination.select("a")
        if not page_links:
            return 1

        max_page = 1
        for link in page_links:
            if link.text.strip() in ["Newer", "Older"]:
                continue
                
            try:
                page_num = int(link.text.strip())
                max_page = max(max_page, page_num)
            except ValueError:
                continue

        return max_page

    async def get_watched_films(self, username: str, session: aiohttp.ClientSession) -> set:
        """Get a set of all films the user has watched (for filtering recommendations)"""
        watched_films = set()
        
        try:
            first_page_url = f"{self.base_url}/{username}/films/"
            first_page_html = await self._fetch_url(session, first_page_url)
            if not first_page_html:
                return watched_films
            
            soup = BeautifulSoup(first_page_html, "html.parser")
            total_pages = self.get_total_pages(soup)
            
            # Process each page to collect film titles
            for page in range(1, min(total_pages + 1, 10)):  # Limit to first 10 pages for performance
                page_url = f"{self.base_url}/{username}/films/page/{page}/" if page > 1 else first_page_url
                if page > 1:
                    page_html = await self._fetch_url(session, page_url)
                    if not page_html:
                        continue
                    soup = BeautifulSoup(page_html, "html.parser")

                film_items = soup.select("li.poster-container")
                
                for item in film_items:
                    film_poster = item.select_one("div.film-poster")
                    if not film_poster or "data-details-endpoint" not in film_poster.attrs:
                        continue

                    json_url = f"{self.base_url}{film_poster['data-details-endpoint']}"
                    film_id = json_url.split('/film/')[-1].split('/')[0]
                    
                    # Try to get cached basic info first
                    cached_basic = self.cache.get_film(film_id, "basic_info")
                    if cached_basic and "title" in cached_basic and "year" in cached_basic:
                        title = cached_basic["title"]
                        year = cached_basic["year"]
                        normalized_title = f"{title.lower().strip()} ({year})"
                        watched_films.add(normalized_title)
                    else:
                        # If not cached, we'd need to fetch it, but for performance, skip for now
                        # In a production system, you might want to fetch these in parallel
                        pass
            
        except Exception as e:
            print(f"Error fetching watched films: {e}")
        
        return watched_films

    def get_watched_films_sync(self, username: str) -> set:
        """Synchronous wrapper for get_watched_films"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._run_watched_films_scraper(username))
        finally:
            loop.close()

    async def _run_watched_films_scraper(self, username: str) -> set:
        """Get watched films with a single session"""
        async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
            return await self.get_watched_films(username, session)
