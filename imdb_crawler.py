import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Set, Dict, Optional, Deque
from collections import deque
import random
import time
from dataclasses import dataclass
from imdb_scraper import IMDBScraper, Movie
import json
import logging
from pathlib import Path
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('imdb_crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CrawlStats:
    """Statistics about the crawl process"""
    total_movies_found: int = 0
    total_movies_processed: int = 0
    successful_scrapes: int = 0
    failed_scrapes: int = 0
    duplicate_movies: int = 0
    movies_by_year: Dict[int, int] = None
    movies_by_genre: Dict[str, int] = None
    depth_reached: int = 0
    movies_at_depth: Dict[int, int] = None
    
    def __post_init__(self):
        self.movies_by_year = {}
        self.movies_by_genre = {}
        self.movies_at_depth = {}
    
    def update(self, movie: Optional[Movie] = None, is_duplicate: bool = False, depth: int = 0):
        """Update statistics with a new movie"""
        self.total_movies_processed += 1
        self.depth_reached = max(self.depth_reached, depth)
        self.movies_at_depth[depth] = self.movies_at_depth.get(depth, 0) + 1
        
        if movie:
            self.successful_scrapes += 1
            if not is_duplicate:
                self.total_movies_found += 1
                # Update year stats
                self.movies_by_year[movie.year] = self.movies_by_year.get(movie.year, 0) + 1
                # Update genre stats
                for genre in movie.genres:
                    self.movies_by_genre[genre] = self.movies_by_genre.get(genre, 0) + 1
            else:
                self.duplicate_movies += 1
        else:
            self.failed_scrapes += 1
    
    def print_summary(self):
        """Print a summary of the crawl statistics"""
        logger.info("\nCrawl Statistics Summary:")
        logger.info(f"Total movies found: {self.total_movies_found}")
        logger.info(f"Total movies processed: {self.total_movies_processed}")
        logger.info(f"Successful scrapes: {self.successful_scrapes}")
        logger.info(f"Failed scrapes: {self.failed_scrapes}")
        logger.info(f"Duplicate movies: {self.duplicate_movies}")
        logger.info(f"Maximum depth reached: {self.depth_reached}")
        
        logger.info("\nMovies by Depth:")
        for depth in sorted(self.movies_at_depth.keys()):
            logger.info(f"Depth {depth}: {self.movies_at_depth[depth]} movies")
        
        logger.info("\nMovies by Year:")
        for year in sorted(self.movies_by_year.keys()):
            logger.info(f"{year}: {self.movies_by_year[year]}")
        
        logger.info("\nTop 10 Genres:")
        for genre, count in sorted(self.movies_by_genre.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"{genre}: {count}")

class IMDBCrawler:
    def __init__(self, 
                 target_movie_count: int = 2000,
                 min_year: int = 1950,
                 min_rating: float = 6.0,
                 min_votes: int = 1000,
                 max_depth: int = 5,
                 output_dir: str = "src/data"):
        """
        Initialize the IMDB crawler
        
        Args:
            target_movie_count: Number of movies to collect
            min_year: Minimum year for movies
            min_rating: Minimum IMDB rating
            min_votes: Minimum number of votes
            max_depth: Maximum depth for BFS crawl
            output_dir: Directory to save the database
        """
        self.scraper = IMDBScraper()
        self.target_count = target_movie_count
        self.min_year = min_year
        self.min_rating = min_rating
        self.min_votes = min_votes
        self.max_depth = max_depth
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = CrawlStats()
        self.movie_cache: Dict[str, Movie] = {}  # Cache for movies we've already seen
        self.queue: Deque[tuple[str, int]] = deque()  # (movie_id, depth)
        self.visited: Set[str] = set()  # Set of visited movie IDs
        
        # Seed movies to start the crawl
        self.seed_movies = [
            'tt0111161',  # The Shawshank Redemption
            'tt0068646',  # The Godfather
            'tt0468569',  # The Dark Knight
            'tt0071562',  # The Godfather Part II
            'tt0050083',  # 12 Angry Men
            'tt0108052',  # Schindler's List
            'tt0167260',  # The Lord of the Rings: The Return of the King
            'tt0110912',  # Pulp Fiction
            'tt0120737',  # The Lord of the Rings: The Fellowship of the Ring
            'tt0060196',  # The Good, the Bad and the Ugly
        ]
    
    async def crawl(self):
        """Main crawl method using BFS"""
        logger.info(f"Starting IMDB crawl for {self.target_count} movies")
        logger.info(f"Minimum year: {self.min_year}, Minimum rating: {self.min_rating}, Minimum votes: {self.min_votes}")
        logger.info(f"Maximum depth: {self.max_depth}")
        
        # Initialize queue with seed movies
        for movie_id in self.seed_movies:
            self.queue.append((movie_id, 0))  # Start at depth 0
        
        # BFS crawl
        while self.queue:
            movie_id, depth = self.queue.popleft()
            
            # Skip if we've already visited this movie
            if movie_id in self.visited:
                continue
            
            self.visited.add(movie_id)
            
            try:
                # Scrape movie details
                movie = self.scraper.scrape_movie_details(movie_id)
                
                # Validate movie meets our criteria
                if (movie and 
                    movie.year >= self.min_year and 
                    movie.rating >= self.min_rating and 
                    movie.num_votes >= self.min_votes):
                    
                    # Add to cache if not already present
                    if movie_id not in self.movie_cache:
                        self.movie_cache[movie_id] = movie
                        self.stats.update(movie, depth=depth)
                        
                        # If we haven't reached max depth, get related movies
                        if depth < self.max_depth:
                            related_movies = await self._get_related_movies(movie_id)
                            for related_id in related_movies:
                                if related_id not in self.visited:
                                    self.queue.append((related_id, depth + 1))
                    else:
                        self.stats.update(movie, is_duplicate=True, depth=depth)
                else:
                    self.stats.update(None, depth=depth)
                
                # Save progress periodically
                if len(self.movie_cache) % 50 == 0:
                    self._save_progress()
                
                # Rate limiting
                if len(self.movie_cache) == self.target_count:
                    logger.info("Target movie count (" + str(self.target_count) + ") reached; continuing crawl (press Ctrl+C to stop).")
                await asyncio.sleep(random.uniform(1, 2))
                
            except Exception as e:
                logger.error(f"Error processing movie {movie_id}: {e}")
                self.stats.update(None, depth=depth)
        
        # Final save
        self._save_progress()
        
        # Print statistics
        self.stats.print_summary()
    
    async def _get_related_movies(self, movie_id: str) -> Set[str]:
        """Get related movies from 'More Like This' and 'You May Also Like' sections"""
        related_movies = set()
        try:
            url = f"{self.scraper.base_url}/title/{movie_id}/"
            async with aiohttp.ClientSession(headers=self.scraper.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Look for "More Like This" and "You May Also Like" sections
                        sections = []
                        # Find by class (legacy)
                        sections += soup.find_all(['div', 'section'], class_=lambda x: x and ('more-like-this' in x.lower() or 'recommendations' in x.lower()))
                        # Find by data-testid (modern)
                        sections += soup.find_all('section', attrs={'data-testid': 'MoreLikeThis'})
                        
                        for section in sections:
                            # Find all movie links in these sections
                            movie_links = section.find_all('a', href=re.compile(r'/title/tt\d+'))
                            for link in movie_links:
                                href = link.get('href', '')
                                movie_id_match = re.search(r'/title/(tt\d+)', href)
                                if movie_id_match:
                                    related_movies.add(movie_id_match.group(1))
            
            logger.info(f"Found {len(related_movies)} related movies for {movie_id}")
            
        except Exception as e:
            logger.error(f"Error getting related movies for {movie_id}: {e}")
        
        return related_movies
    
    def _save_progress(self):
        """Save current progress to JSON file, merging with any existing database so that if the crawler is interrupted (e.g. by Ctrl+C) and then restarted, it does not overwrite (and hence lose) movies saved in a previous run."""
        try:
            output_file = self.output_dir / "movie_database.json"
            # Read existing movies (if any) from the file
            existing_movies = {}
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    for m_dict in json.load(f):
                        existing_movies[m_dict["imdb_id"]] = m_dict
            # Merge (or overwrite) with current in-memory cache
            for movie in self.movie_cache.values():
                m_dict = movie.to_dict()
                existing_movies[m_dict["imdb_id"]] = m_dict
            # Write the merged (or overwritten) list back to the file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(list(existing_movies.values()), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved (merged) {len(existing_movies)} movies to {output_file} (current cache: {len(self.movie_cache)})")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")

async def main():
    """Main function to run the crawler"""
    crawler = IMDBCrawler(
        target_movie_count=2000,
        min_year=1950,
        min_rating=6.0,
        min_votes=1000,
        max_depth=5,
        output_dir="src/data"
    )
    
    try:
        await crawler.crawl()
    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user. Saving progress...")
        crawler._save_progress()
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        crawler._save_progress()

if __name__ == "__main__":
    asyncio.run(main()) 