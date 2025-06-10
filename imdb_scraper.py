import requests
from bs4 import BeautifulSoup
import json
import time
import random
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
import asyncio
import aiohttp
from dataclasses import dataclass

@dataclass
class Movie:
    """Movie data structure"""
    title: str
    year: int
    director: str
    genres: List[str]
    cast: List[str]
    rating: float
    num_votes: int
    runtime: int
    overview: str
    imdb_id: str
    poster_url: str = ""
    
    def to_dict(self):
        return {
            'title': self.title,
            'year': self.year,
            'director': self.director,
            'genres': self.genres,
            'cast': self.cast[:5],  # Limit to top 5 cast members
            'rating': self.rating,
            'num_votes': self.num_votes,
            'runtime': self.runtime,
            'overview': self.overview,
            'imdb_id': self.imdb_id,
            'poster_url': self.poster_url
        }

class IMDBScraper:
    def __init__(self):
        self.base_url = "https://www.imdb.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_top_movies_lists(self) -> List[str]:
        """Get URLs for various IMDB top movie lists"""
        lists = [
            "/chart/top/",  # Top 250
            "/chart/moviemeter/",  # Most Popular Movies
            "/search/title/?title_type=feature&num_votes=25000,&sort=user_rating,desc&count=250",  # Highly rated with many votes
            "/search/title/?title_type=feature&year=2020,2024&num_votes=10000,&sort=user_rating,desc&count=250",  # Recent highly rated
            "/search/title/?title_type=feature&year=2010,2019&num_votes=25000,&sort=user_rating,desc&count=250",  # 2010s highly rated
            "/search/title/?title_type=feature&year=2000,2009&num_votes=25000,&sort=user_rating,desc&count=250",  # 2000s highly rated
            "/search/title/?title_type=feature&year=1990,1999&num_votes=25000,&sort=user_rating,desc&count=250",  # 1990s highly rated
            "/search/title/?title_type=feature&genres=action&num_votes=25000,&sort=user_rating,desc&count=100",  # Top Action
            "/search/title/?title_type=feature&genres=comedy&num_votes=25000,&sort=user_rating,desc&count=100",  # Top Comedy
            "/search/title/?title_type=feature&genres=drama&num_votes=25000,&sort=user_rating,desc&count=100",  # Top Drama
            "/search/title/?title_type=feature&genres=horror&num_votes=25000,&sort=user_rating,desc&count=100",  # Top Horror
            "/search/title/?title_type=feature&genres=sci-fi&num_votes=25000,&sort=user_rating,desc&count=100",  # Top Sci-Fi
            "/search/title/?title_type=feature&genres=thriller&num_votes=25000,&sort=user_rating,desc&count=100",  # Top Thriller
        ]
        return lists
    
    def scrape_movie_list(self, list_url: str) -> List[str]:
        """Scrape a list page and return movie IDs"""
        movie_ids = []
        try:
            print(f"Scraping list: {list_url}")
            response = self.session.get(self.base_url + list_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find movie links - different selectors for different page types
            movie_links = []
            
            # For top charts
            movie_links.extend(soup.select('h3.titleColumn a[href*="/title/tt"]'))
            movie_links.extend(soup.select('a.titleColumn[href*="/title/tt"]'))
            
            # For search results
            movie_links.extend(soup.select('h3.ipc-title a[href*="/title/tt"]'))
            movie_links.extend(soup.select('.lister-item-header a[href*="/title/tt"]'))
            
            # For newer IMDB layouts
            movie_links.extend(soup.select('a[class*="titleColumn"][href*="/title/tt"]'))
            movie_links.extend(soup.select('a.cli-title[href*="/title/tt"]'))
            
            for link in movie_links:
                href = link.get('href', '')
                if '/title/tt' in href:
                    movie_id = re.search(r'/title/(tt\d+)', href)
                    if movie_id:
                        movie_ids.append(movie_id.group(1))
            
            print(f"Found {len(movie_ids)} movies in list")
            time.sleep(random.uniform(1, 2))  # Rate limiting
            
        except Exception as e:
            print(f"Error scraping list {list_url}: {e}")
        
        return movie_ids
    
    def scrape_movie_details(self, movie_id: str) -> Optional[Movie]:
        """Scrape detailed information for a specific movie"""
        try:
            url = f"{self.base_url}/title/{movie_id}/"
            print(f"Scraping movie: {movie_id}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title and year
            title_element = soup.select_one('h1[data-testid="hero__pageTitle"] span')
            if not title_element:
                title_element = soup.select_one('h1.sc-afe43def-0')
            if not title_element:
                title_element = soup.select_one('h1')
            
            title = title_element.text.strip() if title_element else "Unknown"
            
            # Extract year
            year = 0
            year_elements = soup.select('a[href*="/year/"]')
            for year_elem in year_elements:
                year_text = year_elem.text.strip()
                if year_text.isdigit() and 1900 <= int(year_text) <= 2030:
                    year = int(year_text)
                    break
            
            if year == 0:
                year_match = re.search(r'\((\d{4})\)', soup.text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Extract director
            director = "Unknown"
            director_links = soup.select('a[href*="/name/nm"]')
            for link in director_links:
                parent_text = link.parent.get_text() if link.parent else ""
                if any(word in parent_text.lower() for word in ['director', 'directed']):
                    director = link.text.strip()
                    break
            
            # Extract genres
            genres = []
            genre_elements = soup.select('a[href*="/search/title/?genres="]')
            for genre_elem in genre_elements[:5]:  # Limit to first 5 genres
                genre_text = genre_elem.text.strip()
                if genre_text and genre_text not in genres:
                    genres.append(genre_text)
            
            # Extract cast
            cast = []
            cast_elements = soup.select('a[data-testid="cast-item-characters-link"]')
            if not cast_elements:
                cast_elements = soup.select('td.primary_photo + td a')
            
            for cast_elem in cast_elements[:5]:  # Top 5 cast members
                cast_name = cast_elem.text.strip()
                if cast_name and cast_name not in cast:
                    cast.append(cast_name)
            
            # Extract rating
            rating = 0.0
            rating_elements = soup.select('[data-testid="hero-rating-bar__aggregate-rating__score"] span')
            for rating_elem in rating_elements:
                rating_text = rating_elem.text.strip()
                try:
                    rating = float(rating_text)
                    break
                except ValueError:
                    continue
            
            # Extract number of votes
            num_votes = 0
            votes_elements = soup.select('[data-testid="hero-rating-bar__aggregate-rating__vote-count"]')
            for votes_elem in votes_elements:
                votes_text = votes_elem.text.strip()
                votes_match = re.search(r'([\d,]+)', votes_text)
                if votes_match:
                    num_votes = int(votes_match.group(1).replace(',', ''))
                    break
            
            # Extract runtime
            runtime = 0
            runtime_elements = soup.select('li[data-testid="title-techspec_runtime"]')
            for runtime_elem in runtime_elements:
                runtime_text = runtime_elem.text.strip()
                runtime_match = re.search(r'(\d+)\s*(?:min|minute)', runtime_text)
                if runtime_match:
                    runtime = int(runtime_match.group(1))
                    break
            
            # Extract overview/plot
            overview = ""
            plot_elements = soup.select('[data-testid="plot-xl"], [data-testid="plot-l"], [data-testid="plot"]')
            for plot_elem in plot_elements:
                plot_text = plot_elem.text.strip()
                if plot_text:
                    overview = plot_text
                    break
            
            # Extract poster URL
            poster_url = ""
            poster_elements = soup.select('img[data-testid="hero-media__poster"]')
            if not poster_elements:
                poster_elements = soup.select('.ipc-media img')
            
            for poster_elem in poster_elements:
                src = poster_elem.get('src', '')
                if src and 'image' in src:
                    poster_url = src
                    break
            
            movie = Movie(
                title=title,
                year=year,
                director=director,
                genres=genres,
                cast=cast,
                rating=rating,
                num_votes=num_votes,
                runtime=runtime,
                overview=overview,
                imdb_id=movie_id,
                poster_url=poster_url
            )
            
            time.sleep(random.uniform(1, 3))  # Rate limiting
            return movie
            
        except Exception as e:
            print(f"Error scraping movie {movie_id}: {e}")
            return None
    
    def build_movie_database(self, target_count: int = 2000) -> List[Movie]:
        """Build a comprehensive movie database"""
        print(f"Building movie database with target of {target_count} movies...")
        
        all_movie_ids = set()
        movies = []
        
        # Get movie IDs from all lists
        lists = self.get_top_movies_lists()
        for list_url in lists:
            movie_ids = self.scrape_movie_list(list_url)
            all_movie_ids.update(movie_ids)
            
            if len(all_movie_ids) >= target_count * 1.5:  # Get extra to account for failures
                break
        
        print(f"Collected {len(all_movie_ids)} unique movie IDs")
        
        # Shuffle to get variety
        movie_ids_list = list(all_movie_ids)
        random.shuffle(movie_ids_list)
        
        # Scrape movie details
        for i, movie_id in enumerate(movie_ids_list[:target_count * 1.2]):  # Try more than target to account for failures
            if len(movies) >= target_count:
                break
                
            movie = self.scrape_movie_details(movie_id)
            if movie and movie.year > 1950 and movie.rating > 0:  # Basic quality filters
                movies.append(movie)
                print(f"Progress: {len(movies)}/{target_count} movies collected")
            
            # Progress update
            if (i + 1) % 50 == 0:
                print(f"Processed {i + 1} movies, collected {len(movies)} valid movies")
        
        print(f"Successfully collected {len(movies)} movies")
        return movies
    
    def save_database(self, movies: List[Movie], filename: str = "movie_database.json"):
        """Save the movie database to a JSON file"""
        movie_data = [movie.to_dict() for movie in movies]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(movie_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(movies)} movies to {filename}")
    
    def load_database(self, filename: str = "movie_database.json") -> List[Dict]:
        """Load the movie database from a JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Database file {filename} not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Error loading database: {e}")
            return []

def main():
    """Main function to build the movie database"""
    scraper = IMDBScraper()
    
    # Build database
    movies = scraper.build_movie_database(target_count=2000)
    
    # Save to JSON
    scraper.save_database(movies)
    
    # Print some stats
    if movies:
        print(f"\nDatabase Statistics:")
        print(f"Total movies: {len(movies)}")
        print(f"Average rating: {sum(m.rating for m in movies) / len(movies):.2f}")
        print(f"Year range: {min(m.year for m in movies)} - {max(m.year for m in movies)}")
        
        # Genre distribution
        all_genres = []
        for movie in movies:
            all_genres.extend(movie.genres)
        genre_counts = {}
        for genre in all_genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        print(f"Top genres: {sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]}")

if __name__ == "__main__":
    main()