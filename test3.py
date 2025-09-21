import requests

API_KEY = "YOUR_API_KEY"  # Get your free key from https://api-ninjas.com/api/register
BASE_URL = "https://api.api-ninjas.com/v1/airports"

def get_airports_by_country(country_name):
    """
    Fetch airports and their IATA codes for a given country name.
    """
    headers = {"X-Api-Key": API_KEY}
    params = {"country": country_name}
    
    response = requests.get(BASE_URL, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.js