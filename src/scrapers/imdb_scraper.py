import requests
from bs4 import BeautifulSoup
import json
import time
import random
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
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
            "/search/title/?title_type=feature&sort=num_votes,desc",  # Most Voted
            "/search/title/?title_type=feature&sort=user_rating,desc",  # Highest Rated
            "/search/title/?title_type=feature&year=2020-2024&sort=num_votes,desc",  # Recent Popular
            "/search/title/?title_type=feature&year=2010-2019&sort=num_votes,desc",  # 2010s Popular
            "/search/title/?title_type=feature&year=2000-2009&sort=num_votes,desc",  # 2000s Popular
            "/search/title/?title_type=feature&year=1990-1999&sort=num_votes,desc",  # 1990s Popular
            "/search/title/?title_type=feature&year=1980-1989&sort=num_votes,desc",  # 1980s Popular
            "/search/title/?title_type=feature&year=1970-1979&sort=num_votes,desc",  # 1970s Popular
            "/search/title/?title_type=feature&year=1960-1969&sort=num_votes,desc",  # 1960s Popular
            "/search/title/?title_type=feature&year=1950-1959&sort=num_votes,desc",  # 1950s Popular
        ]
        return lists
    
    def scrape_movie_list(self, list_url: str) -> List[str]:
        """Scrape a list page and return movie IDs"""
        movie_ids = set()  # Use set to avoid duplicates
        try:
            print(f"Scraping list: {list_url}")
            
            # For search pages, we need to handle pagination
            if "search/title" in list_url:
                # Add parameters for more results per page and start position
                base_url = self.base_url + list_url
                if "?" in base_url:
                    base_url += "&"
                else:
                    base_url += "?"
                base_url += "count=250"  # Get 250 results per page
                
                # Try multiple pages
                for start in range(1, 1001, 250):  # Get up to 1000 movies from each search
                    url = f"{base_url}&start={start}"
                    print(f"Scraping page {start//250 + 1}...")
                    
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find all movie links
                    movie_links = soup.find_all('a', href=re.compile(r'/title/tt\d+'))
                    page_movie_ids = set()
                    
                    for link in movie_links:
                        href = link.get('href', '')
                        movie_id_match = re.search(r'/title/(tt\d+)', href)
                        if movie_id_match:
                            page_movie_ids.add(movie_id_match.group(1))
                    
                    if not page_movie_ids:  # No more movies found
                        break
                        
                    movie_ids.update(page_movie_ids)
                    print(f"Found {len(page_movie_ids)} movies on page {start//250 + 1}")
                    
                    # Check if we've hit the end of results
                    if "Next »" not in response.text:
                        break
                        
                    time.sleep(random.uniform(2, 3))  # Rate limiting between pages
            else:
                # For chart pages (top 250, moviemeter)
                response = self.session.get(self.base_url + list_url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all movie links
                movie_links = soup.find_all('a', href=re.compile(r'/title/tt\d+'))
                for link in movie_links:
                    href = link.get('href', '')
                    movie_id_match = re.search(r'/title/(tt\d+)', href)
                    if movie_id_match:
                        movie_ids.add(movie_id_match.group(1))
            
            print(f"Found {len(movie_ids)} unique movies in list")
            time.sleep(random.uniform(1, 2))  # Rate limiting between lists
            
        except Exception as e:
            print(f"Error scraping list {list_url}: {e}")
        
        return list(movie_ids)  # Convert set back to list
    
    def scrape_movie_details(self, movie_id: str) -> Optional[Movie]:
        """Scrape detailed information for a specific movie"""
        try:
            url = f"{self.base_url}/title/{movie_id}/"
            print(f"Scraping movie: {movie_id}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title - look for the main heading
            title = "Unknown"
            title_candidates = [
                soup.find('h1'),
                soup.find('h1', class_=True),
                soup.select_one('[data-testid="hero__pageTitle"]'),
                soup.select_one('h1[data-testid="hero__pageTitle"]')
            ]
            
            for candidate in title_candidates:
                if candidate:
                    title_text = candidate.get_text().strip()
                    if title_text and title_text != "Unknown":
                        title = title_text
                        break
            
            # Extract year from the text
            year = 0
            page_text = soup.get_text()
            year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', page_text)
            if year_matches:
                # Take the first reasonable year
                for year_str in year_matches:
                    year_int = int(year_str)
                    if 1900 <= year_int <= 2030:
                        year = year_int
                        break
            
            # Extract rating
            rating = 0.0
            rating_pattern = r'(\d+\.\d+)/10'
            rating_matches = re.findall(rating_pattern, page_text)
            if rating_matches:
                try:
                    rating = float(rating_matches[0])
                except (ValueError, IndexError):
                    pass
            
            # Extract director
            director = "Unknown"
            
            # Try to find director from structured HTML first
            director_links = soup.find_all('a', href=re.compile(r'/name/nm\d+'))
            for link in director_links:
                # Get the surrounding text to see if it mentions director
                parent = link.parent
                if parent:
                    parent_text = parent.get_text().lower()
                    # Look for director-related keywords near the link
                    if any(word in parent_text for word in ['director', 'directed']):
                        director_name = link.get_text().strip()
                        # Only accept reasonable name lengths
                        if len(director_name.split()) <= 3 and len(director_name) < 30:
                            director = director_name
                            break
            
            # If still not found, try text patterns but be more specific
            if director == "Unknown":
                # Look for "Director: Name" or "Directed by Name" patterns
                director_patterns = [
                    r'Director\s*:?\s*([A-Z][a-zA-Z\.\s]{2,25}?)(?:\s|Writer|Star|$)',
                    r'Directed by\s*([A-Z][a-zA-Z\.\s]{2,25}?)(?:\s|Writer|Star|$)',
                ]
                
                for pattern in director_patterns:
                    director_matches = re.findall(pattern, page_text)
                    if director_matches:
                        potential_director = director_matches[0].strip()
                        # Clean up common issues
                        potential_director = re.sub(r'\s+', ' ', potential_director)  # Remove extra spaces
                        if len(potential_director) < 30 and not any(word in potential_director.lower() for word in ['writer', 'star', 'see']):
                            director = potential_director
                            break
            
            # Extract runtime with better validation
            runtime = 0
            runtime_patterns = [
                r'(\d{1,3})h\s*(\d{1,2})m',  # 2h 22m
                r'(\d{1,3})\s*h\s*(\d{1,2})\s*m',  # 2 h 22 m
            ]
            
            for pattern in runtime_patterns:
                runtime_matches = re.findall(pattern, page_text)
                if runtime_matches:
                    hours, minutes = runtime_matches[0]
                    hours, minutes = int(hours), int(minutes)
                    # Validate reasonable runtime (5 minutes to 10 hours)
                    if 0 <= hours <= 10 and 0 <= minutes < 60:
                        runtime = hours * 60 + minutes
                        break
            
            # If no h/m format found, try minutes only
            if runtime == 0:
                minutes_patterns = [
                    r'(\d{2,3})\s*(?:min|minutes)',  # 120 min
                ]
                for pattern in minutes_patterns:
                    minutes_matches = re.findall(pattern, page_text)
                    if minutes_matches:
                        minutes = int(minutes_matches[0])
                        # Validate reasonable runtime (5 to 600 minutes)
                        if 5 <= minutes <= 600:
                            runtime = minutes
                            break
            
            # Extract number of votes with better parsing
            num_votes = 0
            # Look for patterns like "9.3 (3.1M)" or "Rating: 8.6/10 from 1.6M users"
            votes_patterns = [
                r'\((\d+\.?\d*[KM])\)',  # (3.1M)
                r'(\d+\.?\d*[KM])\s*(?:users?|votes?|ratings?)',  # 3.1M users
                r'from\s*(\d+\.?\d*[KM])\s*(?:users?|votes?)',  # from 3.1M users
                r'(\d+,\d+)\s*(?:users?|votes?)',  # 1,234,567 votes
            ]
            
            for pattern in votes_patterns:
                votes_matches = re.findall(pattern, page_text, re.IGNORECASE)
                if votes_matches:
                    votes_str = votes_matches[0]
                    try:
                        if 'K' in votes_str:
                            num_votes = int(float(votes_str.replace('K', '')) * 1000)
                        elif 'M' in votes_str:
                            num_votes = int(float(votes_str.replace('M', '')) * 1000000)
                        else:
                            num_votes = int(votes_str.replace(',', ''))
                        
                        # Validate reasonable vote count
                        if 10 <= num_votes <= 10000000:  # 10 to 10M votes
                            break
                        else:
                            num_votes = 0
                    except (ValueError, IndexError):
                        continue
            
            # Extract cast with better parsing
            cast = []
            # Look for structured cast information
            cast_links = soup.find_all('a', href=re.compile(r'/name/nm\d+'))
            potential_cast = []
            
            for link in cast_links:
                name = link.get_text().strip()
                # Skip if it's likely not a cast member
                if (len(name.split()) <= 3 and 
                    len(name) < 30 and 
                    name not in ['Director', 'Writer', 'Producer'] and
                    not any(skip_word in name.lower() for skip_word in ['see', 'more', 'info', 'imdb'])):
                    potential_cast.append(name)
            
            # Remove duplicates and take top 5
            seen = set()
            for name in potential_cast:
                if name not in seen and len(cast) < 5:
                    cast.append(name)
                    seen.add(name)
            
            # Extract overview with better patterns
            overview = ""
            
            # First try meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                meta_content = meta_desc.get('content', '').strip()
                # Check if it looks like a good plot description
                if (50 <= len(meta_content) <= 500 and 
                    not any(skip_word in meta_content.lower() for skip_word in ['imdb', 'rating', 'watch', 'trailer'])):
                    overview = meta_content
            
            # If meta description isn't good, try other patterns
            if not overview or len(overview) < 50:
                plot_patterns = [
                    r'(?:Plot|Story|Synopsis)[:\s]*([^\.]{50,300}\.)',
                    r'([A-Z][^\.]{100,400}\.)',  # Sentences that look like plot descriptions
                ]
                
                for pattern in plot_patterns:
                    plot_matches = re.findall(pattern, page_text, re.IGNORECASE)
                    for match in plot_matches:
                        match = match.strip()
                        # Check if it looks like a plot (not just random text)
                        if (50 <= len(match) <= 500 and 
                            not any(skip_word in match.lower() for skip_word in 
                                   ['imdb', 'rating', 'watch', 'trailer', 'see production', 'writer', 'director'])):
                            overview = match
                            break
                    if overview:
                        break
            
            # Extract genres from text
            genres = []
            common_genres = ['Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime', 
                           'Documentary', 'Drama', 'Family', 'Fantasy', 'Film Noir', 'History', 
                           'Horror', 'Music', 'Musical', 'Mystery', 'Romance', 'Sci-Fi', 
                           'Science Fiction', 'Sport', 'Thriller', 'War', 'Western', 'Epic', 
                           'Period Drama', 'Prison Drama']
            
            for genre in common_genres:
                if genre in page_text and genre not in genres:
                    genres.append(genre)
                if len(genres) >= 5:  # Limit to 5 genres
                    break
            
            # Extract poster URL
            poster_url = ""
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src', '')
                alt = img.get('alt', '')
                if 'media-cache' in src or 'images' in src:
                    if title.lower() in alt.lower() or 'poster' in alt.lower():
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
