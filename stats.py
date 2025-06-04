from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class UserProfile:
    """User's viewing profile for recommendations"""
    username: str
    total_films: int = 0
    average_rating: float = 0
    preferred_genres: Dict[str, int] = None
    preferred_directors: Dict[str, int] = None
    preferred_decades: Dict[str, int] = None
    rating_distribution: Dict[str, int] = None
    watched_films: set = None
    high_rated_films: List[Dict] = None  # Films rated 4+ stars
    
    def __post_init__(self):
        if self.preferred_genres is None:
            self.preferred_genres = {}
        if self.preferred_directors is None:
            self.preferred_directors = {}
        if self.preferred_decades is None:
            self.preferred_decades = {}
        if self.rating_distribution is None:
            self.rating_distribution = {}
        if self.watched_films is None:
            self.watched_films = set()
        if self.high_rated_films is None:
            self.high_rated_films = []


class StatsCalculator:
    """Handles calculation of user statistics for recommendation purposes"""
    
    def __init__(self):
        pass
    
    def calculate_user_profile(self, raw_stats: Dict) -> UserProfile:
        """Convert raw stats into a structured user profile"""
        profile = UserProfile(username=raw_stats.get('username', ''))
        
        profile.total_films = raw_stats.get('total_films', 0)
        profile.average_rating = raw_stats.get('average_rating', 0)
        
        # Extract top preferences (most frequent genres, directors, etc.)
        if 'top_genres' in raw_stats and raw_stats['top_genres']:
            profile.preferred_genres = raw_stats['top_genres']
        
        if 'top_directors' in raw_stats and raw_stats['top_directors']:
            profile.preferred_directors = raw_stats['top_directors']
            
        if 'top_decades' in raw_stats and raw_stats['top_decades']:
            profile.preferred_decades = raw_stats['top_decades']
            
        if 'rating_distribution' in raw_stats and raw_stats['rating_distribution']:
            profile.rating_distribution = raw_stats['rating_distribution']
        
        return profile
    
    def identify_genre_preferences(self, genres_data: Dict[str, int], min_threshold: int = 2) -> List[str]:
        """Identify user's preferred genres based on frequency"""
        if not genres_data:
            return []
        
        # Get genres watched more than the threshold
        preferred = [genre for genre, count in genres_data.items() if count >= min_threshold]
        
        # Sort by frequency
        preferred.sort(key=lambda x: genres_data[x], reverse=True)
        
        return preferred[:10]  # Top 10 preferred genres
    
    def identify_director_preferences(self, directors_data: Dict[str, int], min_threshold: int = 2) -> List[str]:
        """Identify user's preferred directors"""
        if not directors_data:
            return []
        
        preferred = [director for director, count in directors_data.items() if count >= min_threshold]
        preferred.sort(key=lambda x: directors_data[x], reverse=True)
        
        return preferred[:15]  # Top 15 preferred directors
    
    def calculate_rating_tendency(self, rating_dist: Dict[str, int]) -> str:
        """Determine if user is generous, critical, or average with ratings"""
        if not rating_dist:
            return "unknown"
        
        total_ratings = sum(rating_dist.values())
        if total_ratings == 0:
            return "unknown"
        
        # Calculate percentage of high ratings (4+ stars)
        high_ratings = sum(count for rating, count in rating_dist.items() 
                          if float(rating) >= 4.0)
        high_rating_percentage = (high_ratings / total_ratings) * 100
        
        # Calculate percentage of low ratings (2.5 and below)
        low_ratings = sum(count for rating, count in rating_dist.items() 
                         if float(rating) <= 2.5)
        low_rating_percentage = (low_ratings / total_ratings) * 100
        
        if high_rating_percentage > 40:
            return "generous"
        elif low_rating_percentage > 30:
            return "critical"
        else:
            return "balanced"
    
    def get_decade_preferences(self, decades_data: Dict[str, int]) -> List[str]:
        """Get preferred decades in order"""
        if not decades_data:
            return []
        
        # Sort decades by count
        sorted_decades = sorted(decades_data.items(), key=lambda x: x[1], reverse=True)
        return [decade for decade, count in sorted_decades if count > 1]
    
    def calculate_diversity_score(self, genres_data: Dict[str, int]) -> float:
        """Calculate how diverse the user's genre preferences are"""
        if not genres_data or len(genres_data) < 2:
            return 0.0
        
        total_films = sum(genres_data.values())
        if total_films == 0:
            return 0.0
        
        # Calculate entropy-like measure
        genre_percentages = [count / total_films for count in genres_data.values()]
        diversity = -sum(p * (p.bit_length() - 1) for p in genre_percentages if p > 0)
        
        # Normalize to 0-1 scale
        max_diversity = len(genres_data).bit_length() - 1
        return min(diversity / max_diversity if max_diversity > 0 else 0, 1.0)