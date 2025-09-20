from serpapi import GoogleSearch
from serpapi.google_search import GoogleSearch

params = {
  "engine": "google_images_light",
  "q": "Coffee",
  "api_key": "9f7573a0965a1bf5ea63d3943aa0c81f972210c57e36afc0b60fca22d53ec3e2"
}

search = GoogleSearch(params)
results = search.get_dict()
images_results = results["images_results"]
for image in images_results:
    print(image)