import time
import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from typing import List
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
import os, re, json, logging
# from serpapi import GoogleSearch
from serpapi import GoogleSearch
from serpapi.google_search import GoogleSearch
import random
import requests
# --- Environment Variable Setup ---
# Load environment variables from a .env file for security
load_dotenv()

# --- Gemini API Configuration ---
# Configure the generative AI model with the API key from environment variables
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except KeyError:
    # This provides a clear error if the API key is not set
    raise RuntimeError("GEMINI_API_KEY not found in environment variables. Please create a .env file and add it.")


# --- Pydantic Models for Data Validation ---
# These models ensure the data sent to and received from the API is structured correctly.
class TripDetails(BaseModel):
    source: str
    destination: str
    startDate: str
    endDate: str
    duration: int
    travelers: int
    interests: List[str]
    budget: int

class Activity(BaseModel):
    type: str
    time: str
    title: str
    description: str
    image: str

class DayPlan(BaseModel):
    day: int
    title: str
    summary: str
    activities: List[Activity]


class Itinerary(BaseModel):
    title: str
    days: List[DayPlan]
    totalCost: int
    image_url: str | None = None   # 👈 add this

# --- FastAPI App Initialization ---
app = FastAPI(
    title="TripsAI API",
    description="API for generating personalized travel itineraries using Google Gemini.",
    version="2.0.0"
)

# --- CORS Middleware ---
# Allows the frontend to communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://127.0.0.1:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
CITY_NAME_FIXES = {
    "bangalore": "Kempegowda Int",
    "mumbai": "Chhatrapati Shivaji",
    "Kolkata": "Netaji Subhas Chandra",
    # add more aliases if needed
}

def normalize_city(city: str) -> str:
    return CITY_NAME_FIXES.get(city.lower(), city)



# --- AI Prompt Engineering Function ---
# This function creates the detailed prompt for the Gemini AI model.
def create_gemini_prompt(details: TripDetails) -> str:
    interests_str = ", ".join(details.interests)
    
    # The JSON structure is explicitly defined in the prompt to ensure the AI returns a valid response.
    # This is a key part of "prompt engineering".
    json_format_instructions = """
    {
      "title": "A string for the itinerary title",
      "days": [
        {
          "day": "An integer for the day number",
          "title": "A string for the day's theme or title",
          "summary": "A short string summary of the day",
          "activities": [
            {
              "type": "A string for the activity type (e.g., 'foodie', 'adventure')",
              "time": "A string for the time of day (e.g., 'Morning', 'Afternoon', 'Evening')",
              "title": "A string for the activity title",
              "description": "A string describing the activity",
              "image": "A string URL for a placeholder image from 'https://placehold.co/100x100/..."
            }
          ]
        }
      ],
      "totalCost": "An integer representing the total estimated cost in INR"
    }
    """

    prompt = f"""
    You are an expert travel planner for India. Your task is to create a personalized travel itinerary based on the user's preferences.
    
    **User Preferences:**
    - source: {details.source}
    - Destination: {details.destination}
    - Duration: {details.duration} days
    - Number of Travelers: {details.travelers}
    - Budget (per person): INR {details.budget}
    - Interests: {interests_str}

    **Your Task:**
    1.  Generate a creative, logical, and exciting day-by-day itinerary.
    2.  The `totalCost` should be a realistic estimate in INR for the specified number of travelers, considering the budget level.
    3.  For each `activity` in the `itinerary`, the `description` should be detailed. Include specific, realistic (but fictional) details like:
        - **Famous food places:** Suggest a well-known local eatery and a famous dish to try.
        - **Visiting hours:** Mention typical opening and closing times for attractions (e.g., "open from 9 AM to 5 PM").
        - **Hotels and Flights:** Suggest realistic hotel names and approximate prices per night, and mention flight details (e.g., "A morning flight with IndiGo").
    4.  For each activity, provide a relevant placeholder image URL from `https://placehold.co/`. For example: `https://placehold.co/100x100/3498db/ffffff?text=Beach`.
    5.  The final output MUST be a single, valid JSON object that strictly follows this structure. Do not include any text, explanations, or markdown formatting before or after the JSON object.

    **Required JSON Structure:**
    {json_format_instructions}
    """
    return prompt


# --- API Endpoint ---
# @app.post("/api/generate-itinerary", response_model=Itinerary)
# async def generate_itinerary_endpoint(details: TripDetails):
#     """
#     Accepts trip details, sends them to the Gemini model, and returns a personalized itinerary.
#     """
#     print("Received request with details:", details.model_dump_json(indent=2))
    
#     prompt = create_gemini_prompt(details)
    
#     try:
#         # Send the prompt to the Gemini model
#         response = model.generate_content(prompt)
        
#         # Clean up the response to ensure it's valid JSON
#         # The AI can sometimes wrap the JSON in markdown backticks
#         cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        
#         print("--- Gemini Raw Response ---")
#         print(cleaned_response_text)
#         print("---------------------------")

#         # Parse the JSON string from the AI's response
#         itinerary_data = json.loads(cleaned_response_text)
#         # ✅ Add image_url if not provided by AI
#         if "image_url" not in itinerary_data or not itinerary_data["image_url"]:
#             encoded_destination = details.destination.replace(" ", "+")
#             itinerary_data["image_url"] = f"https://source.unsplash.com/1200x600/?{encoded_destination},travel"

        
#         # Validate the data against our Pydantic model
#         # This ensures the AI's output matches our required structure.
#         itinerary = Itinerary(**itinerary_data)
#         return itinerary

#     except (json.JSONDecodeError, ValidationError) as e:
#         print(f"Error processing AI response: {e}")
#         # If the AI response is not valid JSON or doesn't match our model, return an error.
#         raise HTTPException(
#             status_code=500, 
#             detail="Failed to process the itinerary from the AI. The response was not in the expected format."
#         )
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         # Catch any other potential errors (e.g., API connection issues)
#         raise HTTPException(
#             status_code=500, 
#             detail=f"An unexpected error occurred while generating the itinerary: {str(e)}"
#         )


# @app.get("/api/flights")
# async def search_flights(query: str):
#     """
#     Search for flights using SerpApi.
#     """
#     try:
#         if not os.environ.get("SERPAPI_KEY"):
#             raise ValueError("SERPAPI_KEY is not set in environment variables.")

#         params = {
#             "engine": "google_flights",
#             "q": query,
#             "api_key": os.environ.get("SERPAPI_KEY")
#         }

#         search = GoogleSearch(params)
#         results = search.get_dict()
        
#         # You can process and simplify the results here if needed
#         return {"results": results.get("best_flights", [])}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to search flights: {str(e)}")

async def get_airport_code(city: str):
    """
    Fetches the IATA airport code for a given city name.
    
    Args:
        city (str): The name of the city.

    Returns:
        str: The IATA airport code, or None if not found.
    """
    airport_mapping = {
        "bangalore": "BLR",
        "delhi": "DEL",
        "mumbai": "BOM",
        "chennai": "MAA",
        "kolkata": "CCU",
        "pune": "PNQ",
        "ahmedabad": "AMD",
        "hyderabad": "HYD",
        "dubai": "DXB",
        "singapore": "SIN",
        "london": "LHR",
        "new york": "JFK",
        "san francisco": "SFO",
        "tokyo": "HND",
        "paris": "CDG",
    }
    city_lower = city.lower()
    
    if city_lower in airport_mapping:
        return airport_mapping[city_lower]
    
    # If not found in the static map, perform a SerpApi search to find the airport code
    try:
        params = {
            "engine": "google_flights",
            "q": f"airport code for {city} airport",
            "api_key": os.environ.get("SERPAPI_KEY")
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        if "departure_airport" in results.get("search_parameters", {}):
            return results["search_parameters"]["departure_airport"]
        
        return None

    except Exception as e:
        print(f"Error fetching airport code for {city}: {e}")
        return None



@app.get("/api/flights/search")
async def get_flights(source: str = Query(..., description="Source city or airport code"),
                      destination: str = Query(..., description="Destination city or airport code"),
                      date: str = Query(None, description="Travel date in YYYY-MM-DD format (optional)")):
    """
    Fetches flight data based on source, destination, and an optional date.
    """
    print(f"Received request for flights from {source} to {destination} on {date}")
    
    # Get airport codes for source and destination
    source_code = await get_airport_code(source)
    destination_code = await get_airport_code(destination)
    
    if not source_code or not destination_code:
        raise HTTPException(status_code=404, detail="Could not find airport codes for the specified cities.")

    try:
        # Construct the SerpApi query
        params = {
            "engine": "google_flights",
            "departure_id": source_code,
            "arrival_id": destination_code,
            "api_key": os.environ.get("SERPAPI_KEY")
        }
        
        # Add the date parameter if provided
        if date:
            # Validate date format (optional but good practice)
            try:
                datetime.strptime(date, "%Y-%m-%d")
                params["outbound_date"] = date
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD.")
        
        print(f"Searching flights with parameters: {params}")
        
        # Perform the search
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            print(f"SerpApi error: {results['error']}")
            raise HTTPException(status_code=500, detail=results["error"])

        all_flights = []
        
        # Process 'best_flights'
        if "best_flights" in results:
            for flight_data in results["best_flights"]:
                legs = []
                for leg_data in flight_data.get("flights", []):
                    # Format stops and duration
                    stops_str = "Nonstop"
                    stop_details = None
                    if leg_data.get("number_of_stops", 0) > 0:
                        stops_str = f"{leg_data['number_of_stops']} stop"
                        if leg_data['number_of_stops'] > 1:
                            stops_str += "s"
                        
                        # Extract stop airport names if available
                        if leg_data.get("intermediate_airports"):
                             stop_details = "via " + " & ".join(leg_data["intermediate_airports"])

                    # Format duration
                    duration_min = leg_data.get("duration")
                    duration_str = ""
                    if duration_min:
                        hours = duration_min // 60
                        minutes = duration_min % 60
                        duration_str = f"{hours}h {minutes}m"
                        
                    # Format times
                    departure_time = leg_data.get("departure_airport", {}).get("time")
                    arrival_time = leg_data.get("arrival_airport", {}).get("time")
                    if departure_time and arrival_time:
                        # Split from ISO format to get just the time
                        departure_time = departure_time.split('T')[1].split(':')[0:2]
                        arrival_time = arrival_time.split('T')[1].split(':')[0:2]
                        
                        departure_time_dt = datetime.strptime(":".join(departure_time), "%H:%M")
                        arrival_time_dt = datetime.strptime(":".join(arrival_time), "%H:%M")
                        
                        departure_time = departure_time_dt.strftime("%I:%M %p").lstrip('0')
                        arrival_time = arrival_time_dt.strftime("%I:%M %p").lstrip('0')
                        
                        if departure_time[0] == ':':
                            departure_time = '0' + departure_time
                        if arrival_time[0] == ':':
                            arrival_time = '0' + arrival_time
                        
                    
                    
                    leg = FlightLeg(
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                        duration=duration_str,
                        airline=leg_data.get("airline", "Unknown Airline"),
                        stops=stops_str,
                        stop_details=stop_details,
                        flight_number=leg_data.get("flight_number")
                    )
                    legs.append(leg)
                
                flight_option = FlightOption(
                    price=flight_data.get("price", "N/A"),
                    legs=legs
                )
                all_flights.append(flight_option)

        # Process 'other_flights'
        if "other_flights" in results:
            for flight_data in results["other_flights"]:
                # The structure is slightly different, we need to handle it.
                # Assuming the first item in flights is the main leg for simplicity
                if not flight_data.get("flights"):
                    continue
                
                leg_data = flight_data["flights"][0]
                
                # Format stops and duration
                stops_str = "Nonstop"
                stop_details = None
                if leg_data.get("number_of_stops", 0) > 0:
                    stops_str = f"{leg_data['number_of_stops']} stop"
                    if leg_data['number_of_stops'] > 1:
                        stops_str += "s"
                    if leg_data.get("intermediate_airports"):
                         stop_details = "via " + " & ".join(leg_data["intermediate_airports"])
                
                duration_min = leg_data.get("duration")
                duration_str = ""
                if duration_min:
                    hours = duration_min // 60
                    minutes = duration_min % 60
                    duration_str = f"{hours}h {minutes}m"
                
                # Format times
                departure_time = leg_data.get("departure_airport", {}).get("time")
                arrival_time = leg_data.get("arrival_airport", {}).get("time")
                if departure_time and arrival_time:
                    departure_time = departure_time.split('T')[1].split(':')[0:2]
                    arrival_time = arrival_time.split('T')[1].split(':')[0:2]
                    
                    departure_time_dt = datetime.strptime(":".join(departure_time), "%H:%M")
                    arrival_time_dt = datetime.strptime(":".join(arrival_time), "%H:%M")
                    
                    departure_time = departure_time_dt.strftime("%I:%M %p").lstrip('0')
                    arrival_time = arrival_time_dt.strftime("%I:%M %p").lstrip('0')

                    if departure_time[0] == ':':
                        departure_time = '0' + departure_time
                    if arrival_time[0] == ':':
                        arrival_time = '0' + arrival_time

                
                leg = FlightLeg(
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    duration=duration_str,
                    airline=leg_data.get("airline", "Unknown Airline"),
                    stops=stops_str,
                    stop_details=stop_details,
                    flight_number=leg_data.get("flight_number")
                )
                
                flight_option = FlightOption(
                    price=flight_data.get("price", "N/A"),
                    legs=[leg]
                )
                all_flights.append(flight_option)

        return JSONResponse({"flights": [f.model_dump() for f in all_flights]})
    
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/hotels")
async def search_hotels(query: str):
    """
    Search for hotels using SerpApi.
    """
    try:
        if not os.environ.get("SERPAPI_KEY"):
            raise ValueError("SERPAPI_KEY is not set in environment variables.")

        params = {
            "engine": "google_hotels",
            "q": query,
            "api_key": os.environ.get("SERPAPI_KEY")
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        # You can process and simplify the results here if needed
        return {"results": results.get("properties", [])}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search hotels: {str(e)}")



@app.post("/api/generate-itinerary", response_model=Itinerary)
async def generate_itinerary_endpoint(details: TripDetails):
    print("Received request with details:", details.model_dump_json(indent=2))
    
    prompt = create_gemini_prompt(details)
    
    try:
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        itinerary_data = json.loads(cleaned_response_text)

        # ✅ Always add image_url if missing
        if "image_url" not in itinerary_data or not itinerary_data["image_url"]:
            try:
                params = {
                    "engine": "google_images",
                    "q": details.destination,
                    "api_key": os.environ.get("SERPAPI_KEY")  # 🔑 store in .env
                }
                search = GoogleSearch(params)
                results = search.get_dict()
                images_results = results.get("images_results", [])
                # image_url = None  

                # if images_results:
                #     # Filter for results that contain an "original" field
                #     high_res_images = [img for img in images_results if "original" in img]

                #     if high_res_images:
                #         # Pick the image with the largest resolution
                #         best_image = max(
                #             high_res_images,
                #             key=lambda img: img.get("original_width", 0) * img.get("original_height", 0)
                #         )
                #         image_url = best_image["thumbnail"]
                # if not image_url:
                #     encoded_destination = details.destination.replace(" ", "+")
                #     image_url = f"https://source.unsplash.com/1200x600/?{encoded_destination},travel"
                # itinerary_data["image_url"] = image_url

                # if images_results:
                #     image_url = random.choice(images_results)["original"]
                #     itinerary_data["image_url"] = image_url
                if images_results:
                    # ✅ Filter out Google "gstatic" links that block hotlinking
                    valid_images = [
                        img for img in images_results
                        if "original" in img and "gstatic" not in img["original"]
                    ]

                    if valid_images:
                        # Pick the largest resolution image
                        best_image = max(
                            valid_images,
                            key=lambda img: img.get("original_width", 0) * img.get("original_height", 0)
                        )
                        image_url = best_image["original"]
                    else:
                        # Fallback to Unsplash if no valid image found
                        encoded_destination = details.destination.replace(" ", "+")
                        image_url = f"https://source.unsplash.com/1200x600/?{encoded_destination},travel"
                else:
                    # No images at all → fallback to Unsplash
                    encoded_destination = details.destination.replace(" ", "+")
                    image_url = f"https://source.unsplash.com/1200x600/?{encoded_destination},travel"

                itinerary_data["image_url"] = image_url

                
            except Exception as e:
                print(f"Failed to fetch Google image: {e}")
                encoded_destination = details.destination.replace(" ", "+")
                itinerary_data["image_url"] = f"https://source.unsplash.com/1200x600/?{encoded_destination},travel"

        itinerary = Itinerary(**itinerary_data)
        return itinerary

    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Error processing AI response: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to process the itinerary from the AI. The response was not in the expected format."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred while generating the itinerary: {str(e)}"
        )



# @app.get("/background-image")
# def get_background_image(query: str = "Coffee"):
#     params = {
#         "engine": "google_images_light",
#         "q": query,
#         "api_key": "myapi"  # ⚠️ replace with your real key
#     }
#     search = GoogleSearch(params)
#     results = search.get_dict()
#     images_results = results.get("images_results", [])

#     if not images_results:
#         return JSONResponse({"error": "No images found"}, status_code=404)

#     # Pick a random image for variety
#     image_url = random.choice(images_results)["thumbnail"]

#     return {"image_url": image_url}


# @app.get("/api/airports/by-city")
# def get_airports_by_city(city: str):
#     try:
#         # A simple, static lookup for common cities.
#         # In a real-world app, you'd use a more robust airport lookup API.
#         airport_mapping = {
#             "mumbai": "BOM",
#             "bangalore": "BLR",
#             "delhi": "DEL",
#             "chennai": "MAA",
#             "kolkata": "CCU",
#             "hyderabad": "HYD",
#             "kochi": "COK",
#             "goa": "GOI",
#             "pune": "PNQ",
#             "ahmedabad": "AMD",
#             "dubai": "DXB",
#             "singapore": "SIN",
#             "london": "LHR",
#             "new york": "JFK",
#             "san francisco": "SFO",
#             "tokyo": "HND",
#             "paris": "CDG",
#         }
#         city_lower = city.lower()
        
#         if city_lower in airport_mapping:
#             return JSONResponse({"airport_code": airport_mapping[city_lower], "city_name": city})
        
#         # If not found in the static map, perform a SerpApi search to find the airport code
#         params = {
#             "engine": "google_flights",
#             "q": f"airport code for {city}",
#             "api_key": os.environ.get("SERPAPI_KEY")
#         }
#         search = GoogleSearch(params)
#         results = search.get_dict()

#         if "departure_airport" in results.get("search_parameters", {}):
#             airport_code = results["search_parameters"]["departure_airport"]
#             return JSONResponse({"airport_code": airport_code, "city_name": city})
        
#         return JSONResponse({"error": "Airport code not found"}, status_code=404)
        
#     except Exception as e:
#         print(f"Error fetching airport code: {e}")
#         raise HTTPException(status_code=500, detail="Failed to find airport code.")

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/api/flights")
async def get_flights(
    source_city: str = Query(..., description="Source city, e.g. Bangalore"),
    destination_city: str = Query(..., description="Destination city, e.g. Goa"),
    travel_date: str = Query(None, description="Travel date YYYY-MM-DD"),
):
    """
    Use Gemini API to generate flight data between two cities in JSON format.
    """
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Generate a JSON list of at least 3 flight options from {source_city} to {destination_city}.
        Travel date: {travel_date or "any upcoming date"}.

        Each flight must have:
        - departure_airport: name and IATA code
        - arrival_airport: name and IATA code
        - airline
        - airplane
        - duration
        - price (₹INR format)
        - departure_time
        - arrival_time
        - travel_class

        Output ONLY valid JSON. Do not add any text before or after.
        JSON structure:
        {{
          "flights": [ {{ ... }} ]
        }}
        """

        response = model.generate_content(prompt)
        text_output = response.text.strip()

        logger.info("Gemini raw output:\n%s", text_output)

        # --- Step 1: Extract JSON using regex ---
        match = re.search(r"\{[\s\S]*\}", text_output)
        if not match:
            raise HTTPException(status_code=500, detail="Gemini did not return JSON")

        json_str = match.group(0)

        # --- Step 2: Clean common issues ---
        # Remove trailing commas
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

        try:
            flights_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("JSON parsing error: %s\nJSON string:\n%s", e, json_str)
            raise HTTPException(status_code=500, detail=f"Failed to parse JSON: {e}")

        return flights_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch flights from Gemini: {str(e)}")
@app.get("/")
def read_root():
    return {"message": "Welcome to the TripsAI API. Visit /docs for documentation."}

