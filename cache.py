import json
from datetime import datetime, timedelta
import os
import atexit

class Cache:
    def __init__(self, cache_file="cache.json"):
        """Initialize the cache with a JSON file."""
        self.cache_file = cache_file
        self.expiration_days = 30  # Cache films for 30 days since they rarely change
        self.cache_data = {}
        self._load_cache()
        atexit.register(self._save_cache)

    def _load_cache(self):
        """Load the cache from the JSON file."""
        try:
            import builtins #TODO: debug why builtin open isnt found w/o import
            if os.path.exists(self.cache_file):
                with builtins.open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.cache_data = {}

    def _save_cache(self):
        """Save the cache to the JSON file."""
        try:
            import builtins #TODO: debug why builtin open isnt found w/o import
            with builtins.open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def close(self):
        """Save the cache before closing."""
        self._save_cache()

    def __del__(self):
        """Ensure cache is saved when the object is destroyed."""
        self.close()

    def _is_expired(self, timestamp_str):
        """Check if cached data has expired."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            return datetime.now() - timestamp > timedelta(days=self.expiration_days)
        except:
            return True

    def _get_cache_key(self, film_id: str, data_type: str) -> str:
        """Generate a cache key for a specific type of film data."""
        return f"{film_id}:{data_type}"

    def get_film(self, film_id: str, data_type: str = "basic_info"):
        """Get film details from cache for a specific data type."""
        try:
            cache_key = self._get_cache_key(film_id, data_type)
            if cache_key in self.cache_data:
                cached_data = self.cache_data[cache_key]
                if not self._is_expired(cached_data['timestamp']):
                    return cached_data['data']
        except Exception as e:
            print(f"Error reading from film cache for {data_type}: {e}")
        return None

    def set_film(self, film_id: str, film_data, data_type: str = "basic_info"):
        """Cache film details for a specific data type."""
        try:
            cache_key = self._get_cache_key(film_id, data_type)
            cache_entry = {
                'timestamp': datetime.now().isoformat(),
                'data': film_data
            }
            self.cache_data[cache_key] = cache_entry
            # Periodically save cache to file after updates
            self._save_cache()
        except Exception as e:
            print(f"Error caching film data for {data_type}: {e}")

    def clear_expired(self):
        """Clear expired entries from the cache."""
        expired_keys = []
        for key, value in self.cache_data.items():
            try:
                if self._is_expired(value['timestamp']):
                    expired_keys.append(key)
            except:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache_data[key]
            print(f"Cleared expired film data {key} from cache")
        
        if expired_keys:
            self._save_cache() 