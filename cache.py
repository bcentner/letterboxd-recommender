from rocksdict import Rdict
import json
from datetime import datetime, timedelta
import os
import shutil
import atexit

class Cache:
    def __init__(self, db_path=".cache"):
        """Initialize the cache with RocksDB using rocksdict."""
        self.db_path = db_path
        self.films_db = None
        self.expiration_days = 30  # Cache films for 30 days since they rarely change
        
        # Register cleanup on exit
        atexit.register(self.close)
        
        # Try to initialize database
        self._initialize_database()

    def _initialize_database(self):
        """Initialize the database with proper error handling."""
        # Create cache directory if it doesn't exist
        os.makedirs(self.db_path, exist_ok=True)
        
        try:
            # Try to open existing database
            self.films_db = Rdict(os.path.join(self.db_path, "films.db"))
        except Exception as e:
            print(f"Error opening database: {e}")
            # If we get a lock error, try to clean up and recreate
            if "Resource temporarily unavailable" in str(e):
                print("Detected locked database, attempting cleanup...")
                self._cleanup_database()
                try:
                    # Try to open again after cleanup
                    self.films_db = Rdict(os.path.join(self.db_path, "films.db"))
                except Exception as e2:
                    print(f"Error reopening database after cleanup: {e2}")
                    raise
            else:
                raise

    def _cleanup_database(self):
        """Clean up database files and locks."""
        try:
            # Close any open connections
            if self.films_db:
                self.films_db.close()
            
            # Remove the database directory
            films_path = os.path.join(self.db_path, "films.db")
            
            if os.path.exists(films_path):
                shutil.rmtree(films_path)
                
            print("Successfully cleaned up database files")
        except Exception as e:
            print(f"Error during database cleanup: {e}")
            raise

    def close(self):
        """Close the database connection."""
        try:
            if self.films_db:
                self.films_db.close()
                self.films_db = None
        except Exception as e:
            print(f"Error closing database: {e}")

    def __del__(self):
        """Ensure database is closed when the object is destroyed."""
        self.close()

    def _is_expired(self, timestamp_str):
        """Check if cached data has expired."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            return datetime.now() - timestamp > timedelta(days=self.expiration_days)
        except:
            return True

    def get_film(self, film_id):
        """Get film details from cache."""
        try:
            if film_id in self.films_db:
                cached_data = json.loads(self.films_db[film_id])
                if not self._is_expired(cached_data['timestamp']):
                    return cached_data['data']
        except Exception as e:
            print(f"Error reading from film cache: {e}")
        return None

    def set_film(self, film_id, film_data):
        """Cache film details."""
        try:
            cache_entry = {
                'timestamp': datetime.now().isoformat(),
                'data': film_data
            }
            self.films_db[film_id] = json.dumps(cache_entry)
        except Exception as e:
            print(f"Error caching film data: {e}")

    def clear_expired(self):
        """Clear expired entries from the database."""
        expired_keys = []
        for key, value in self.films_db.items():
            try:
                cached_data = json.loads(value)
                if self._is_expired(cached_data['timestamp']):
                    expired_keys.append(key)
            except:
                expired_keys.append(key)
        
        # Delete expired keys
        for key in expired_keys:
            del self.films_db[key]
            print(f"Cleared expired film {key} from cache") 