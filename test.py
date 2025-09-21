from serpapi import GoogleSearch
from serpapi.google_search import GoogleSearch
import os
import requests


params = {
  "engine": "google_images",
  "q": "Coffee",
  "api_key": "9f7573a0965a1bf5ea63d3943aa0c81f972210c57e36afc0b60fca22d53ec3e2"
}

# Create folder to save images
folder_path = "downloaded_images"
os.makedirs(folder_path, exist_ok=True)

# Perform the search
search = GoogleSearch(params)
results = search.get_dict()
images_results = results["images_results"]

# Loop through images and save them
for idx, image in enumerate(images_results):
    print(f"Downloading image {idx + 1}: {image['title']}")
    # image_url = image.get("original")  # use original image URL
    print(image)
    # if not image:
    #     continue

    # try:
    #     response = requests.get(image)
    #     response.raise_for_status()  # check for request errors

    #     # Get file extension
    #     ext = image.split(".")[-1].split("?")[0]  # handle URLs with query params
    #     file_path = os.path.join(folder_path, f"coffee_{idx}.{ext}")

    #     # Save image
    #     with open(file_path, "wb") as f:
    #         f.write(response.content)

    #     print(f"Saved: {file_path}")
    # except Exception as e:
    #     print(f"Failed to download {image_url}: {e}")