from serpapi import GoogleSearch

params = {
  "engine": "google_flights",
  "departure_id": "PAE",
  "arrival_id": "JFK",
  "outbound_date": "2025-09-20",
  "return_date": "2025-09-26",
  "currency": "USD",
  "hl": "en",
  "api_key": "9f7573a0965a1bf5ea63d3943aa0c81f972210c57e36afc0b60fca22d53ec3e2"
}

search = GoogleSearch(params)
results = search.get_dict()
print(results)