import requests
from bs4 import BeautifulSoup

BASE_URL = "https://letterboxd.com"
USERNAME = "bcentner"  
FILMS_URL = f"{BASE_URL}/{USERNAME}/films/by/rated-date/page/{{}}/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_films_with_ratings(page_number):
    url = FILMS_URL.format(page_number)
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch page {page_number}")
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')
    films = soup.select("li.poster-container")
    
    film_ratings = {}
    for film in films:
        img_tag = film.find("img", alt=True)
        rating_tag = film.select_one("p.poster-viewingdata span.rating")
        
        if img_tag and rating_tag:
            title = img_tag["alt"].strip()
            rating = rating_tag.get_text(strip=True)
            film_ratings[title] = rating

    return film_ratings

# Example: Scrape first 2 pages
all_film_ratings = {}
for i in range(1, 3):
    all_film_ratings.update(get_films_with_ratings(i))

print(f"Collected {len(all_film_ratings)} films with ratings:")
for title, rating in all_film_ratings.items():
    print(f"{title}: {rating}")
