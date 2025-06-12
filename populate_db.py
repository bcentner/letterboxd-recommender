from imdb_scraper import IMDBScraper

def main():
    """Main function to build the movie database"""
    print("Starting to build movie database...")
    scraper = IMDBScraper()
    
    # Build database with 2000 movies
    print("Fetching movies from IMDB...")
    movies = scraper.build_movie_database(target_count=2000)
    
    # Save to JSON
    print("Saving movies to database...")
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