import requests
import json
import random
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from stats import UserProfile, StatsCalculator
from collections import defaultdict, Counter
import time


@dataclass
class MovieRecommendation:
    """A movie recommendation with scoring details"""
    title: str
    year: str
    director: str
    genres: List[str]
    overview: str
    poster_url: str
    tmdb_id: Optional[str] = None
    letterboxd_url: Optional[str] = None
    score: float = 0.0
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class MovieRecommendationEngine:
    """Generates movie recommendations based on user's Letterboxd profile"""
    
    def __init__(self, tmdb_api_key: Optional[str] = None):
        self.tmdb_api_key = tmdb_api_key
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.letterboxd_base_url = "https://letterboxd.com"
        self.stats_calculator = StatsCalculator()
        
        # Common genres mapping for TMDB
        self.genre_mapping = {
            "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35,
            "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751,
            "Fantasy": 14, "History": 36, "Horror": 27, "Music": 10402,
            "Mystery": 9648, "Romance": 10749, "Science Fiction": 878,
            "TV Movie": 10770, "Thriller": 53, "War": 10752, "Western": 37
        }
    
    def generate_recommendations(self, user_profile: UserProfile, num_recommendations: int = 20) -> List[MovieRecommendation]:
        """Generate movie recommendations for a user"""
        recommendations = []
        
        try:
            # Get recommendations from multiple sources
            if self.tmdb_api_key:
                tmdb_recs = self._get_tmdb_recommendations(user_profile, num_recommendations // 2)
                recommendations.extend(tmdb_recs)
            
            # Get genre-based recommendations
            genre_recs = self._get_genre_based_recommendations(user_profile, num_recommendations // 3)
            recommendations.extend(genre_recs)
            
            # Get director-based recommendations  
            director_recs = self._get_director_based_recommendations(user_profile, num_recommendations // 4)
            recommendations.extend(director_recs)
            
            # Remove duplicates and filter out watched films
            recommendations = self._deduplicate_and_filter(recommendations, user_profile.watched_films)
            
            # Score and rank recommendations
            scored_recommendations = self._score_recommendations(recommendations, user_profile)
            
            # Return top recommendations
            return sorted(scored_recommendations, key=lambda x: x.score, reverse=True)[:num_recommendations]
            
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return []
    
    def _get_tmdb_recommendations(self, user_profile: UserProfile, count: int) -> List[MovieRecommendation]:
        """Get recommendations from TMDB API based on user preferences"""
        if not self.tmdb_api_key:
            return []
        
        recommendations = []
        
        try:
            # Get popular movies in preferred genres
            preferred_genres = list(user_profile.preferred_genres.keys())[:3]
            
            for genre in preferred_genres:
                genre_id = self.genre_mapping.get(genre)
                if genre_id:
                    url = f"{self.tmdb_base_url}/discover/movie"
                    params = {
                        "api_key": self.tmdb_api_key,
                        "with_genres": genre_id,
                        "sort_by": "popularity.desc",
                        "vote_average.gte": 6.5,  # Only well-rated films
                        "page": 1
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        for movie in data.get("results", [])[:count//3]:
                            rec = self._create_recommendation_from_tmdb(movie, [f"Popular in {genre}"])
                            if rec:
                                recommendations.append(rec)
                    time.sleep(0.1)  # Rate limiting
                    
        except Exception as e:
            print(f"Error fetching TMDB recommendations: {e}")
        
        return recommendations
    
    def _create_recommendation_from_tmdb(self, movie_data: Dict, reasons: List[str]) -> Optional[MovieRecommendation]:
        """Create a MovieRecommendation from TMDB data"""
        try:
            # Get genre names
            genre_names = []
            if "genre_ids" in movie_data:
                genre_map = {v: k for k, v in self.genre_mapping.items()}
                genre_names = [genre_map.get(gid, "Unknown") for gid in movie_data["genre_ids"]]
            
            poster_url = ""
            if movie_data.get("poster_path"):
                poster_url = f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"
            
            return MovieRecommendation(
                title=movie_data.get("title", "Unknown"),
                year=movie_data.get("release_date", "")[:4] if movie_data.get("release_date") else "",
                director="Unknown",  # TMDB discover doesn't include director
                genres=genre_names,
                overview=movie_data.get("overview", ""),
                poster_url=poster_url,
                tmdb_id=str(movie_data.get("id", "")),
                reasons=reasons
            )
        except Exception as e:
            print(f"Error creating recommendation from TMDB data: {e}")
            return None
    
    def _get_genre_based_recommendations(self, user_profile: UserProfile, count: int) -> List[MovieRecommendation]:
        """Get recommendations based on user's genre preferences using curated lists"""
        recommendations = []
        
        # Curated film database (normally you'd fetch this from a real API)
        genre_films = self._get_curated_films_by_genre()
        
        preferred_genres = list(user_profile.preferred_genres.keys())[:5]
        
        for genre in preferred_genres:
            if genre in genre_films:
                films = genre_films[genre]
                sample_size = min(count // len(preferred_genres), len(films))
                selected_films = random.sample(films, sample_size)
                
                for film in selected_films:
                    rec = MovieRecommendation(
                        title=film["title"],
                        year=film["year"],
                        director=film["director"],
                        genres=film["genres"],
                        overview=film.get("overview", ""),
                        poster_url=film.get("poster_url", ""),
                        letterboxd_url=film.get("letterboxd_url", ""),
                        reasons=[f"You enjoy {genre} films"]
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    def _get_director_based_recommendations(self, user_profile: UserProfile, count: int) -> List[MovieRecommendation]:
        """Get recommendations based on user's director preferences"""
        recommendations = []
        
        # Get films by preferred directors that user hasn't seen
        director_films = self._get_curated_films_by_director()
        
        preferred_directors = list(user_profile.preferred_directors.keys())[:3]
        
        for director in preferred_directors:
            if director in director_films:
                films = director_films[director]
                sample_size = min(count // len(preferred_directors), len(films))
                selected_films = random.sample(films, sample_size)
                
                for film in selected_films:
                    rec = MovieRecommendation(
                        title=film["title"],
                        year=film["year"],
                        director=director,
                        genres=film["genres"],
                        overview=film.get("overview", ""),
                        poster_url=film.get("poster_url", ""),
                        letterboxd_url=film.get("letterboxd_url", ""),
                        reasons=[f"Directed by {director}, who you've enjoyed before"]
                    )
                    recommendations.append(rec)
        
        return recommendations
    
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
            
            # Score based on genre match
            genre_score = 0
            for genre in rec.genres:
                if genre in user_profile.preferred_genres:
                    genre_score += user_profile.preferred_genres[genre]
            
            if genre_score > 0:
                score += min(genre_score / 10, 3.0)  # Cap genre score at 3.0
            
            # Score based on director match
            if rec.director in user_profile.preferred_directors:
                director_boost = user_profile.preferred_directors[rec.director]
                score += min(director_boost / 5, 2.0)  # Cap director score at 2.0
                
            # Score based on decade preference
            if rec.year and len(rec.year) >= 4:
                try:
                    decade = f"{(int(rec.year) // 10) * 10}s"
                    if decade in user_profile.preferred_decades:
                        score += min(user_profile.preferred_decades[decade] / 10, 1.0)
                except ValueError:
                    pass
            
            # Add base popularity score
            score += 1.0
            
            rec.score = score
        
        return recommendations
    
    def _get_curated_films_by_genre(self) -> Dict[str, List[Dict]]:
        """Returns a curated database of films by genre (normally would be from external API)"""
        return {
            "Drama": [
                {"title": "Parasite", "year": "2019", "director": "Bong Joon-ho", "genres": ["Drama", "Thriller"], "overview": "A poor family schemes to become employed by a wealthy family."},
                {"title": "The Godfather", "year": "1972", "director": "Francis Ford Coppola", "genres": ["Drama", "Crime"], "overview": "The patriarch of a crime family transfers control to his reluctant son."},
                {"title": "Moonlight", "year": "2016", "director": "Barry Jenkins", "genres": ["Drama"], "overview": "A young black man grapples with his identity and sexuality."},
                {"title": "Manchester by the Sea", "year": "2016", "director": "Kenneth Lonergan", "genres": ["Drama"], "overview": "A man is forced to care for his nephew after his brother's death."},
                {"title": "Her", "year": "2013", "director": "Spike Jonze", "genres": ["Drama", "Romance", "Science Fiction"], "overview": "A man develops a relationship with an AI operating system."}
            ],
            "Comedy": [
                {"title": "The Grand Budapest Hotel", "year": "2014", "director": "Wes Anderson", "genres": ["Comedy", "Adventure"], "overview": "The adventures of a legendary concierge and his protégé."},
                {"title": "In Bruges", "year": "2008", "director": "Martin McDonagh", "genres": ["Comedy", "Crime"], "overview": "Two hitmen hide out in Bruges after a job gone wrong."},
                {"title": "Hunt for the Wilderpeople", "year": "2016", "director": "Taika Waititi", "genres": ["Comedy", "Adventure"], "overview": "A boy and his foster uncle become fugitives in the New Zealand bush."},
                {"title": "What We Do in the Shadows", "year": "2014", "director": "Taika Waititi", "genres": ["Comedy", "Horror"], "overview": "Mockumentary about vampires sharing a flat in New Zealand."},
                {"title": "Kiss Kiss Bang Bang", "year": "2005", "director": "Shane Black", "genres": ["Comedy", "Crime"], "overview": "A petty thief becomes involved in a murder investigation."}
            ],
            "Horror": [
                {"title": "Hereditary", "year": "2018", "director": "Ari Aster", "genres": ["Horror", "Drama"], "overview": "A family is haunted by tragedy and sinister secrets."},
                {"title": "The Wailing", "year": "2016", "director": "Na Hong-jin", "genres": ["Horror", "Mystery"], "overview": "A stranger arrives in a village and mysterious deaths begin."},
                {"title": "It Follows", "year": "2014", "director": "David Robert Mitchell", "genres": ["Horror"], "overview": "A supernatural entity stalks a young woman."},
                {"title": "The Babadook", "year": "2014", "director": "Jennifer Kent", "genres": ["Horror", "Drama"], "overview": "A mother and son are tormented by a sinister presence."},
                {"title": "Midsommar", "year": "2019", "director": "Ari Aster", "genres": ["Horror", "Drama"], "overview": "A couple travels to Sweden for a festival that turns sinister."}
            ],
            "Science Fiction": [
                {"title": "Blade Runner 2049", "year": "2017", "director": "Denis Villeneuve", "genres": ["Science Fiction"], "overview": "A young blade runner discovers a secret that could plunge society into chaos."},
                {"title": "Arrival", "year": "2016", "director": "Denis Villeneuve", "genres": ["Science Fiction", "Drama"], "overview": "A linguist works with the military to communicate with aliens."},
                {"title": "Ex Machina", "year": "2014", "director": "Alex Garland", "genres": ["Science Fiction", "Thriller"], "overview": "A programmer is selected to participate in a ground-breaking AI experiment."},
                {"title": "Under the Skin", "year": "2013", "director": "Jonathan Glazer", "genres": ["Science Fiction", "Horror"], "overview": "An alien preys on men in Scotland."},
                {"title": "Annihilation", "year": "2018", "director": "Alex Garland", "genres": ["Science Fiction", "Horror"], "overview": "A biologist signs up for a dangerous expedition into a mysterious zone."}
            ]
        }
    
    def _get_curated_films_by_director(self) -> Dict[str, List[Dict]]:
        """Returns a curated database of films by director"""
        return {
            "Christopher Nolan": [
                {"title": "Dunkirk", "year": "2017", "genres": ["War", "Drama"], "overview": "Allied soldiers are surrounded by enemy forces during WWII."},
                {"title": "Interstellar", "year": "2014", "genres": ["Science Fiction", "Drama"], "overview": "A team of explorers travel through a wormhole in space."},
                {"title": "The Prestige", "year": "2006", "genres": ["Mystery", "Thriller"], "overview": "Two stage magicians engage in competitive one-upmanship."}
            ],
            "Denis Villeneuve": [
                {"title": "Dune", "year": "2021", "genres": ["Science Fiction", "Adventure"], "overview": "Paul Atreides leads a rebellion to free his desert world."},
                {"title": "Sicario", "year": "2015", "genres": ["Crime", "Thriller"], "overview": "An FBI agent is enlisted in the war against drugs."},
                {"title": "Prisoners", "year": "2013", "genres": ["Crime", "Thriller"], "overview": "A desperate father searches for his missing daughter."}
            ],
            "Wes Anderson": [
                {"title": "Isle of Dogs", "year": "2018", "genres": ["Animation", "Comedy"], "overview": "A boy journeys to find his exiled dog on a trash island."},
                {"title": "The Royal Tenenbaums", "year": "2001", "genres": ["Comedy", "Drama"], "overview": "An estranged family of former child prodigies reunites."},
                {"title": "Moonrise Kingdom", "year": "2012", "genres": ["Comedy", "Drama"], "overview": "Two twelve-year-olds fall in love and run away together."}
            ]
        }