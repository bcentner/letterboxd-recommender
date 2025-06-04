# Letterboxd Movie Recommendation System

A personalized movie recommendation system that analyzes your Letterboxd viewing history to suggest films you might enjoy. The system considers your genre preferences, favorite directors, rating patterns, and viewing habits to generate tailored recommendations.

## Features

- **Personalized Recommendations**: Analyzes your complete Letterboxd viewing history
- **Multi-factor Analysis**: Considers genres, directors, decades, and rating patterns
- **Smart Filtering**: Excludes films you've already watched
- **Beautiful UI**: Modern, responsive web interface with movie posters
- **Configurable Options**: Choose what data to analyze for recommendations
- **Caching System**: Efficient caching to speed up subsequent analyses

## How It Works

1. **Profile Analysis**: Scrapes your Letterboxd profile to understand your viewing preferences
2. **Pattern Recognition**: Identifies your preferred genres, directors, and rating tendencies
3. **Recommendation Generation**: Uses multiple algorithms to suggest films based on:
   - Genre preferences with frequency weighting
   - Director preferences from your viewing history
   - Decade/era preferences
   - Rating patterns (generous vs. critical)
4. **Smart Scoring**: Ranks recommendations based on multiple preference factors
5. **Filtering**: Removes films you've already logged on Letterboxd

## Installation

### Prerequisites
- Python 3.8+
- Virtual environment support

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd letterboxd-recommendations
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and go to `http://localhost:5000`

## Usage

1. **Enter Username**: Input your Letterboxd username on the homepage
2. **Select Options**: Choose what data to analyze:
   - **Analyze Genres** (Recommended): Analyzes your genre preferences
   - **Analyze Cast**: More detailed analysis but slower processing
   - **Analyze Ratings**: Considers your rating patterns
3. **Set Recommendations Count**: Choose how many recommendations to generate (10-25)
4. **Get Recommendations**: Click the button and wait for processing (1-2 minutes for large collections)

## Project Structure

```
├── app.py                 # Flask web application
├── scraper.py            # Letterboxd scraping functionality  
├── stats.py              # User statistics and profile analysis
├── recommendation.py     # Recommendation engine and algorithms
├── cache.py              # Caching system for performance
├── templates/            # HTML templates
│   ├── index.html        # Homepage with input form
│   ├── recommendations.html  # Results page
│   ├── results.html      # Original stats page
│   └── error.html        # Error handling page
└── requirements.txt      # Python dependencies
```

## Core Components

### Scraper (`scraper.py`)
- Asynchronous web scraping of Letterboxd profiles
- Fetches film data including titles, years, directors, genres, and ratings
- Handles pagination and rate limiting
- Caches film data for performance

### Stats Calculator (`stats.py`)
- Analyzes viewing patterns and preferences
- Calculates user profiles with genre/director preferences
- Determines rating tendencies (generous, critical, balanced)
- Computes diversity scores for viewing habits

### Recommendation Engine (`recommendation.py`)
- Multi-source recommendation generation
- Genre-based recommendations from curated database
- Director-based suggestions
- Optional TMDB API integration for enhanced recommendations
- Scoring and ranking system for recommendations

### Caching System (`cache.py`)
- JSON-based caching for film metadata
- 30-day expiration for film data
- Automatic cleanup of expired entries
- Performance optimization for repeated analysis

## Configuration

### TMDB API (Optional)
For enhanced recommendations, you can add a TMDB API key:

```bash
export TMDB_API_KEY="your_api_key_here"
```

Without TMDB, the system uses a curated database of quality films.

### Customization
- Modify curated film databases in `recommendation.py`
- Adjust recommendation scoring weights
- Configure cache settings in `cache.py`
- Customize UI in the templates directory

## Performance Notes

- **Processing Time**: 1-3 minutes for users with 100+ films
- **Memory Usage**: Lightweight, works on basic systems
- **Caching**: Subsequent runs for the same user are much faster
- **Rate Limiting**: Built-in delays to respect Letterboxd's servers

## Technical Details

### Algorithms
- **Genre Scoring**: Frequency-based weighting with normalization
- **Director Matching**: Filmography analysis excluding watched films
- **Decade Preferences**: Historical period analysis
- **Rating Tendency**: Statistical analysis of rating distribution

### Data Sources
- **Primary**: Letterboxd user profiles and film pages
- **Secondary**: Curated film database with quality selections
- **Optional**: TMDB API for additional metadata and recommendations

## Limitations

- **Rate Limiting**: Processing speed limited by respectful scraping
- **Profile Dependency**: Requires public Letterboxd profiles
- **Data Scope**: Limited to films available on Letterboxd
- **Language**: Currently optimized for English-language film data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please respect Letterboxd's terms of service and use responsibly.

## Disclaimer

This tool is for personal use only. Please respect Letterboxd's servers by not running excessive requests. The recommendation quality depends on your viewing history size and diversity.

---

*Built with Flask, BeautifulSoup, and ❤️ for movie lovers*