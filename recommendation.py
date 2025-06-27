import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from stats import UserProfile, StatsCalculator
from collections import defaultdict, Counter
import math


@dataclass
class MovieRecommendation:
    """A movie recommendation with scoring details"""
    title: str
    year: str
    director: str
    genres: List[str]
    overview: str
    poster_url: str
    imdb_id: str = None
    tmdb_id: Optional[str] = None
    letterboxd_url: Optional[str] = None
    score: float = 0.0
    reasons: List[str] = None
    rating: float = 0.0
    num_votes: int = 0
    runtime: int = 0
    cast: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
        if self.cast is None:
            self.cast = []


class MovieRecommendationEngine:
    """Generates movie recommendations based on user's Letterboxd profile"""
    
    def __init__(self, tmdb_api_key: Optional[str] = None, movie_db_file: str = "movie_database.json"):
        self.tmdb_api_key = tmdb_api_key
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.letterboxd_base_url = "https://letterboxd.com"
        self.stats_calculator = StatsCalculator()
        self.movie_db_file = movie_db_file
        
        # Load our movie database on initialization
        self.movie_database = self._load_movie_database()
        print(f"Loaded {len(self.movie_database)} movies from database")
        
        # Create lookup indexes for efficient querying
        self._create_indexes()
        
        # Common genres mapping for TMDB (kept for backward compatibility)
        self.genre_mapping = {
            "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35,
            "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751,
            "Fantasy": 14, "History": 36, "Horror": 27, "Music": 10402,
            "Mystery": 9648, "Romance": 10749, "Science Fiction": 878,
            "TV Movie": 10770, "Thriller": 53, "War": 10752, "Western": 37
        }
    
    def _load_movie_database(self) -> List[Dict]:
        """Load the movie database from JSON file"""
        try:
            with open(self.movie_db_file, 'r', encoding='utf-8') as f:
                database = json.load(f)
            
            validated_database = self._validate_database(database)
            print(f"Loaded and validated {len(validated_database)} movies from {self.movie_db_file}")
            return validated_database
            
        except FileNotFoundError:
            print(f"Warning: Movie database file {self.movie_db_file} not found. Using fallback data.")
            return self._get_fallback_movies()
        except json.JSONDecodeError as e:
            print(f"Error loading movie database: {e}. Using fallback data.")
            return self._get_fallback_movies()
    
    def _validate_database(self, database: List[Dict]) -> List[Dict]:
        """Validate that the database conforms to our standards"""
        if not isinstance(database, list):
            print("Error: Database must be a list of movies")
            return self._get_fallback_movies()
        
        validated_movies = []
        required_fields = ['title', 'year', 'director', 'genres', 'rating', 'num_votes', 'runtime', 'overview', 'imdb_id']
        
        for i, movie in enumerate(database):
            if not isinstance(movie, dict):
                print(f"Warning: Skipping invalid movie at index {i} (not a dictionary)")
                continue
            
            missing_fields = [field for field in required_fields if field not in movie]
            if missing_fields:
                print(f"Warning: Skipping movie '{movie.get('title', 'Unknown')}' - missing fields: {missing_fields}")
                continue
            
            try:
                year = int(movie['year'])
                if not (1900 <= year <= 2030):
                    print(f"Warning: Skipping movie '{movie['title']}' - invalid year: {year}")
                    continue
                
                rating = float(movie['rating'])
                if not (0 <= rating <= 10):
                    print(f"Warning: Skipping movie '{movie['title']}' - invalid rating: {rating}")
                    continue
                
                num_votes = int(movie['num_votes'])
                if num_votes < 0:
                    print(f"Warning: Skipping movie '{movie['title']}' - invalid vote count: {num_votes}")
                    continue
                
                runtime = int(movie['runtime'])
                if runtime <= 0:
                    print(f"Warning: Skipping movie '{movie['title']}' - invalid runtime: {runtime}")
                    continue
                
                if not isinstance(movie['genres'], list) or not all(isinstance(g, str) for g in movie['genres']):
                    print(f"Warning: Skipping movie '{movie['title']}' - invalid genres format")
                    continue
                
                if 'cast' in movie and not isinstance(movie['cast'], list):
                    movie['cast'] = []
                elif 'cast' not in movie:
                    movie['cast'] = []
                
                if 'poster_url' not in movie:
                    movie['poster_url'] = ""
                
                if not movie['imdb_id'].startswith('tt'):
                    print(f"Warning: Skipping movie '{movie['title']}' - invalid IMDB ID format: {movie['imdb_id']}")
                    continue
                
                validated_movies.append(movie)
                
            except (ValueError, TypeError) as e:
                print(f"Warning: Skipping movie '{movie.get('title', 'Unknown')}' - data validation error: {e}")
                continue
        
        if not validated_movies:
            print("Error: No valid movies found in database. Using fallback data.")
            return self._get_fallback_movies()
        
        print(f"Database validation complete: {len(validated_movies)} valid movies out of {len(database)} total")
        return validated_movies
    
    def _get_fallback_movies(self) -> List[Dict]:
        """Fallback movie data if database file is not available"""
        return [
            {
                "title": "The Shawshank Redemption", "year": 1994, "director": "Frank Darabont",
                "genres": ["Drama"], "rating": 9.3, "num_votes": 3100000, "runtime": 142,
                "overview": "Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.",
                "imdb_id": "tt0111161", "poster_url": "", "cast": ["Tim Robbins", "Morgan Freeman"]
            },
            {
                "title": "The Godfather", "year": 1972, "director": "Francis Ford Coppola",
                "genres": ["Crime", "Drama"], "rating": 9.2, "num_votes": 2100000, "runtime": 175,
                "overview": "The patriarch of a crime family transfers control to his reluctant son.",
                "imdb_id": "tt0068646", "poster_url": "", "cast": ["Marlon Brando", "Al Pacino"]
            },
            {
                "title": "The Dark Knight", "year": 2008, "director": "Christopher Nolan",
                "genres": ["Action", "Crime", "Drama"], "rating": 9.0, "num_votes": 3000000, "runtime": 152,
                "overview": "Batman sets out to dismantle the remaining criminal organizations that plague Gotham.",
                "imdb_id": "tt0468569", "poster_url": "", "cast": ["Christian Bale", "Heath Ledger"]
            }
        ]
    
    def _create_indexes(self):
        """Create lookup indexes for efficient querying"""
        self.genre_index = defaultdict(list)
        self.director_index = defaultdict(list)
        self.year_index = defaultdict(list)
        self.cast_index = defaultdict(list)
        
        for i, movie in enumerate(self.movie_database):
            # Index by genres
            for genre in movie.get('genres', []):
                self.genre_index[genre.lower()].append(i)
            
            # Index by director
            director = movie.get('director', '').lower()
            if director and director != 'unknown':
                self.director_index[director].append(i)
            
            # Index by decade
            year = movie.get('year', 0)
            if year:
                decade = (year // 10) * 10
                self.year_index[f"{decade}s"].append(i)
            
            # Index by cast
            for actor in movie.get('cast', []):
                if actor:
                    self.cast_index[actor.lower()].append(i)
    
    def generate_recommendations(self, user_profile: UserProfile, num_recommendations: int = 5) -> List[MovieRecommendation]:
        """Generate movie recommendations for a user based on their profile"""
        try:
            print(f"Generating recommendations for user with {len(user_profile.watched_films)} watched films")
            
            # Get recommendations from multiple sources
            all_recommendations = []
            
            # Genre-based recommendations (40% of results)
            genre_recs = self._get_genre_based_recommendations(user_profile, int(num_recommendations * 0.4))
            all_recommendations.extend(genre_recs)
            
            # Director-based recommendations (30% of results)
            director_recs = self._get_director_based_recommendations(user_profile, int(num_recommendations * 0.3))
            all_recommendations.extend(director_recs)
            
            # Era/decade-based recommendations (20% of results)
            era_recs = self._get_era_based_recommendations(user_profile, int(num_recommendations * 0.2))
            all_recommendations.extend(era_recs)
            
            # Highly-rated discoveries (10% of results)
            discovery_recs = self._get_discovery_recommendations(user_profile, int(num_recommendations * 0.1))
            all_recommendations.extend(discovery_recs)
            
            # Remove duplicates and filter out watched films
            filtered_recs = self._deduplicate_and_filter(all_recommendations, user_profile.watched_films)
            
            # Score and rank recommendations
            scored_recommendations = self._score_recommendations(filtered_recs, user_profile)
            
            # Return top recommendations
            final_recs = sorted(scored_recommendations, key=lambda x: x.score, reverse=True)[:num_recommendations]
            print(f"Generated {len(final_recs)} recommendations")
            
            return final_recs
            
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_genre_based_recommendations(self, user_profile: UserProfile, count: int) -> List[MovieRecommendation]:
        """Get recommendations based on user's preferred genres"""
        recommendations = []
        
        # Get user's top genres
        top_genres = list(user_profile.preferred_genres.keys())[:5]
        
        for genre in top_genres:
            genre_lower = genre.lower()
            if genre_lower in self.genre_index:
                # Get movies in this genre
                movie_indices = self.genre_index[genre_lower]
                
                # Sort by rating and vote count for quality
                sorted_movies = sorted(
                    [self.movie_database[i] for i in movie_indices],
                    key=lambda m: (m.get('rating', 0) * math.log(max(m.get('num_votes', 1), 1))),
                    reverse=True
                )
                
                # Take top movies from this genre
                genre_count = max(1, count // len(top_genres))
                for movie in sorted_movies[:genre_count * 2]:  # Get extra to account for filtering
                    if len(recommendations) >= count:
                        break
                    
                    rec = self._create_recommendation_from_movie(
                        movie, 
                        [f"You enjoy {genre} films ({user_profile.preferred_genres[genre]} watched)"]
                    )
                    if rec:
                        recommendations.append(rec)
        
        return recommendations[:count]
    
    def _get_director_based_recommendations(self, user_profile: UserProfile, count: int) -> List[MovieRecommendation]:
        """Get recommendations based on user's preferred directors"""
        recommendations = []
        
        # Get user's top directors
        top_directors = list(user_profile.preferred_directors.keys())[:3]
        
        for director in top_directors:
            director_lower = director.lower()
            if director_lower in self.director_index:
                # Get movies by this director
                movie_indices = self.director_index[director_lower]
                
                # Sort by rating for quality
                sorted_movies = sorted(
                    [self.movie_database[i] for i in movie_indices],
                    key=lambda m: m.get('rating', 0),
                    reverse=True
                )
                
                # Take top movies from this director
                director_count = max(1, count // len(top_directors))
                for movie in sorted_movies[:director_count * 2]:
                    if len(recommendations) >= count:
                        break
                    
                    rec = self._create_recommendation_from_movie(
                        movie,
                        [f"Directed by {director} ({user_profile.preferred_directors[director]} films watched)"]
                    )
                    if rec:
                        recommendations.append(rec)
        
        return recommendations[:count]
    
    def _get_era_based_recommendations(self, user_profile: UserProfile, count: int) -> List[MovieRecommendation]:
        """Get recommendations based on user's preferred decades"""
        recommendations = []
        
        # Get user's top decades
        top_decades = list(user_profile.preferred_decades.keys())[:3]
        
        for decade in top_decades:
            if decade in self.year_index:
                # Get movies from this decade
                movie_indices = self.year_index[decade]
                
                # Sort by rating and popularity
                sorted_movies = sorted(
                    [self.movie_database[i] for i in movie_indices],
                    key=lambda m: (m.get('rating', 0) * math.log(max(m.get('num_votes', 1), 1))),
                    reverse=True
                )
                
                # Take top movies from this decade
                decade_count = max(1, count // len(top_decades))
                for movie in sorted_movies[:decade_count * 2]:
                    if len(recommendations) >= count:
                        break
                    
                    rec = self._create_recommendation_from_movie(
                        movie,
                        [f"From the {decade} ({user_profile.preferred_decades[decade]} films watched)"]
                    )
                    if rec:
                        recommendations.append(rec)
        
        return recommendations[:count]
    
    def _get_discovery_recommendations(self, user_profile: UserProfile, count: int) -> List[MovieRecommendation]:
        """Get highly-rated films for discovery"""
        recommendations = []
        
        # Get highly-rated films with good vote counts
        highly_rated = sorted(
            self.movie_database,
            key=lambda m: (m.get('rating', 0) * math.log(max(m.get('num_votes', 1), 1))),
            reverse=True
        )
        
        # Take top films that might be discoveries
        for movie in highly_rated[:count * 3]:  # Get extra for filtering
            if len(recommendations) >= count:
                break
            
            # Prefer lesser-known gems (high rating but not too many votes)
            rating = movie.get('rating', 0)
            votes = movie.get('num_votes', 0)
            
            if rating >= 7.5 and 1000 <= votes <= 500000:  # Sweet spot for discoveries
                rec = self._create_recommendation_from_movie(
                    movie,
                    [f"Highly-rated discovery (Rating: {rating}/10)"]
                )
                if rec:
                    recommendations.append(rec)
        
        return recommendations[:count]
    
    def _create_recommendation_from_movie(self, movie_data: Dict, reasons: List[str]) -> Optional[MovieRecommendation]:
        """Create a MovieRecommendation from our database movie data"""
        try:
            return MovieRecommendation(
                title=movie_data.get("title", "Unknown"),
                year=str(movie_data.get("year", "")),
                director=movie_data.get("director", "Unknown"),
                genres=movie_data.get("genres", []),
                overview=movie_data.get("overview", ""),
                poster_url=movie_data.get("poster_url", ""),
                imdb_id=movie_data.get("imdb_id", ""),
                rating=movie_data.get("rating", 0.0),
                num_votes=movie_data.get("num_votes", 0),
                runtime=movie_data.get("runtime", 0),
                cast=movie_data.get("cast", []),
                reasons=reasons
            )
        except Exception as e:
            print(f"Error creating recommendation from movie data: {e}")
            return None
    
    def _deduplicate_and_filter(self, recommendations: List[MovieRecommendation], watched_films: Set[str]) -> List[MovieRecommendation]:
        """Remove duplicates and films the user has already watched"""
        seen_titles = set()
        filtered_recs = []
        
        for rec in recommendations:
            # Create a normalized title for comparison
            normalized_title = f"{rec.title.lower().strip()} ({rec.year})"
            
            if normalized_title not in seen_titles and normalized_title not in watched_films:
                seen_titles.add(normalized_title)
                filtered_recs.append(rec)
        
        return filtered_recs
    
    def _score_recommendations(self, recommendations: List[MovieRecommendation], user_profile: UserProfile) -> List[MovieRecommendation]:
        """Score recommendations based on how well they match user preferences"""
        for rec in recommendations:
            score = 0.0
            reasons = list(rec.reasons)  # Copy existing reasons
            
            # Base score from movie quality
            if rec.rating > 0:
                score += rec.rating / 2  # 0-5 points from rating
            
            if rec.num_votes > 0:
                score += min(math.log(rec.num_votes) / 10, 2.0)  # 0-2 points from popularity
            
            # Score based on genre match
            genre_score = 0
            for genre in rec.genres:
                if genre in user_profile.preferred_genres:
                    genre_weight = user_profile.preferred_genres[genre]
                    genre_score += genre_weight / 10
            
            if genre_score > 0:
                score += min(genre_score, 3.0)  # Cap genre score at 3.0
                reasons.append(f"Matches your genre preferences")
            
            # Score based on director match
            if rec.director in user_profile.preferred_directors:
                director_boost = user_profile.preferred_directors[rec.director]
                score += min(director_boost / 3, 2.0)  # Cap director score at 2.0
                reasons.append(f"By {rec.director}, a director you enjoy")
                
            # Score based on decade preference
            if rec.year and len(rec.year) >= 4:
                try:
                    decade = f"{(int(rec.year) // 10) * 10}s"
                    if decade in user_profile.preferred_decades:
                        decade_boost = user_profile.preferred_decades[decade]
                        score += min(decade_boost / 20, 1.0)  # Cap decade score at 1.0
                        reasons.append(f"From the {decade}, an era you enjoy")
                except ValueError:
                    pass
            
            # Bonus for runtime preferences (avoid very long or very short films)
            if 80 <= rec.runtime <= 180:  # Sweet spot for most viewers
                score += 0.5
            
            rec.score = score
            rec.reasons = reasons
        
        return recommendations
    
    def get_database_stats(self) -> Dict:
        """Get statistics about the loaded movie database"""
        if not self.movie_database:
            return {}
        
        total_movies = len(self.movie_database)
        
        # Year distribution
        years = [movie.get('year', 0) for movie in self.movie_database if movie.get('year', 0) > 0]
        year_range = f"{min(years)} - {max(years)}" if years else "Unknown"
        
        # Genre distribution
        all_genres = []
        for movie in self.movie_database:
            all_genres.extend(movie.get('genres', []))
        genre_counts = Counter(all_genres)
        
        # Rating distribution
        ratings = [movie.get('rating', 0) for movie in self.movie_database if movie.get('rating', 0) > 0]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            'total_movies': total_movies,
            'year_range': year_range,
            'average_rating': round(avg_rating, 2),
            'top_genres': dict(genre_counts.most_common(10)),
            'directors_count': len(self.director_index),
            'database_file': self.movie_db_file
        }