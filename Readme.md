# Letterboxd Movie Recommendation System

A personalized movie recommendation system that analyzes your Letterboxd viewing history to suggest films you might enjoy. The system uses a comprehensive movie database built from IMDB data and considers your genre preferences, favorite directors, rating patterns, and viewing habits to generate tailored recommendations.

## Features

- **Personalized Recommendations**: Analyzes your complete Letterboxd viewing history
- **Comprehensive Movie Database**: Built from IMDB data with 1000+ quality films
- **Multi-factor Analysis**: Considers genres, directors, decades, and rating patterns
- **Smart Filtering**: Excludes films you've already watched
- **Beautiful UI**: Modern, responsive web interface with movie posters
- **Configurable Options**: Choose what data to analyze for recommendations
- **Caching System**: Efficient caching to speed up subsequent analyses
- **Self-contained**: No external API dependencies required

## How It Works

1. **Profile Analysis**: Scrapes your Letterboxd profile to understand your viewing preferences
2. **Pattern Recognition**: Identifies your preferred genres, directors, and rating tendencies
3. **Database Matching**: Uses a comprehensive movie database built from IMDB data
4. **Recommendation Generation**: Uses multiple algorithms to suggest films based on:
   - Genre preferences with frequency weighting (40%)
   - Director preferences from your viewing history (30%)
   - Decade/era preferences (20%)
   - Discovery of highly-rated lesser-known films (10%)
5. **Smart Scoring**: Ranks recommendations based on movie quality and user preference matching
6. **Filtering**: Removes films you've already logged on Letterboxd

## Quick Start

### Prerequisites
- Python 3.8+
- A Letterboxd account with a public profile

### Installation

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd letterboxd-recommender
```

2. **Create and activate a virtual environment**:
```bash
# On Windows:
python -m venv venv
venv\Scripts\activate

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Run the application**:
```bash
python app.py
```

5. **Open your browser** and go to `http://localhost:5000`

## How to Use

### Basic Usage

1. **Enter Your Letterboxd Username**: 
   - Make sure your Letterboxd profile is public
   - Enter your exact username (case-sensitive)

2. **Configure Analysis Options**:
   - **Analyze Genres** (Recommended): Analyzes your genre preferences
   - **Analyze Cast**: More detailed analysis but slower processing
   - **Analyze Ratings**: Considers your rating patterns

3. **Set Recommendations Count**: Choose how many recommendations to generate (10-25)

4. **Get Recommendations**: Click the button and wait for processing
   - Processing time: 1-3 minutes for users with 100+ films
   - Subsequent runs for the same user are much faster due to caching

### Understanding Your Results

The system provides:
- **Personalized Movie Recommendations** with posters and details
- **Your Profile Analysis**: Genre preferences, rating tendencies, favorite directors
- **Database Information**: Stats about the movie database being used
- **Recommendation Reasons**: Why each movie was suggested

### Advanced Features

#### TMDB API Integration (Optional)
For enhanced recommendations, you can add a TMDB API key:

```bash
# On Windows:
set TMDB_API_KEY=your_api_key_here

# On macOS/Linux:
export TMDB_API_KEY="your_api_key_here"
```

Without TMDB, the system uses the built-in movie database with 1000+ quality films.

#### Database Information
Visit `/database` to see detailed information about the movie database, including:
- Total number of movies
- Average ratings
- Genre distribution
- Year range

## Project Structure

```
├── app.py                 # Flask web application
├── scraper.py            # Letterboxd scraping functionality  
├── stats.py              # User statistics and profile analysis
├── recommendation.py     # Recommendation engine and algorithms
├── cache.py              # Caching system for performance
├── movie_database.json   # Comprehensive movie database (1000+ films)
├── imdb_scraper.py       # IMDB data collection tool
├── populate_db.py        # Database building script
├── templates/            # HTML templates
│   ├── index.html        # Homepage with input form
│   ├── recommendations.html  # Results page
│   ├── database.html     # Database information page
│   ├── results.html      # Original stats page
│   └── error.html        # Error handling page
└── requirements.txt      # Python dependencies
```

## Database Management

### Current Database
The system includes a pre-built movie database with:
- **1000+ quality films** from IMDB
- **Comprehensive metadata**: titles, years, directors, genres, cast, ratings
- **Quality filtering**: Movies from 1950+ with good ratings
- **Diverse selection**: Multiple genres, decades, and directors

### Building Your Own Database
To create a custom movie database:

```bash
# Run the IMDB scraper (takes 1-2 hours for 2000 movies)
python populate_db.py
```

This will:
- Scrape movies from IMDB Top 250 and Most Popular lists
- Extract comprehensive metadata for each film
- Save to `movie_database.json`
- Display database statistics

## Troubleshooting

### Common Issues

**"User not found" Error**:
- Ensure your Letterboxd profile is public
- Check that you entered the username correctly (case-sensitive)
- Try visiting your profile URL: `letterboxd.com/yourusername`

**Slow Processing**:
- Large film collections (500+ films) take longer to process
- First-time analysis is slower due to data fetching
- Subsequent runs are faster due to caching

**No Recommendations**:
- Your viewing history might be too small for analysis
- Try enabling more analysis options (genres, cast, ratings)
- Check that you have rated films on Letterboxd

### Performance Tips

- **Use caching**: The system automatically caches data for faster subsequent runs
- **Limit analysis options**: Disable cast analysis for faster processing
- **Reasonable recommendation count**: 10-15 recommendations process faster than 25

## Technical Details

### Recommendation Algorithm
The system uses a multi-strategy approach:
- **Genre-based (40%)**: Movies matching your preferred genres
- **Director-based (30%)**: Films by directors you enjoy
- **Era-based (20%)**: Movies from your preferred decades
- **Discovery (10%)**: Highly-rated lesser-known films

### Scoring System
Each recommendation is scored based on:
- Movie quality (rating × log(votes))
- User preference matching
- Runtime optimization
- Genre/director alignment

### Data Sources
- **Primary**: Letterboxd user profiles and film pages
- **Movie Database**: Built from IMDB data with quality filtering
- **Optional**: TMDB API for additional metadata

## Limitations

- **Public Profiles Only**: Requires public Letterboxd profiles
- **Rate Limiting**: Processing speed limited by respectful scraping
- **Data Scope**: Limited to films available on Letterboxd
- **Language**: Currently optimized for English-language film data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please respect Letterboxd's and IMDB's terms of service and use responsibly.

## Disclaimer

This tool is for personal use only. Please respect Letterboxd's and IMDB's servers by not running excessive requests. The recommendation quality depends on your viewing history size and diversity.

---

*Built with Flask, BeautifulSoup, and ❤️ for movie lovers*