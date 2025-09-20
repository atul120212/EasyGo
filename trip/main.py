import time
import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from typing import List
from dotenv import load_dotenv

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    - Destination: {details.destination}
    - Duration: {details.duration} days
    - Number of Travelers: {details.travelers}
    - Budget (per person): INR {details.budget}
    - Interests: {interests_str}

    **Your Task:**
    1.  Generate a creative, logical, and exciting day-by-day itinerary.
    2.  The `totalCost` should be a realistic estimate in INR for the specified number of travelers, considering the budget level.
    3.  For each activity, provide a relevant placeholder image URL from `https://placehold.co/`. For example: `https://placehold.co/100x100/3498db/ffffff?text=Beach`.
    4.  The final output MUST be a single, valid JSON object that strictly follows this structure. Do not include any text, explanations, or markdown formatting before or after the JSON object.

    **Required JSON Structure:**
    {json_format_instructions}
    """
    return prompt


# --- API Endpoint ---
@app.post("/api/generate-itinerary", response_model=Itinerary)
async def generate_itinerary_endpoint(details: TripDetails):
    """
    Accepts trip details, sends them to the Gemini model, and returns a personalized itinerary.
    """
    print("Received request with details:", details.model_dump_json(indent=2))
    
    prompt = create_gemini_prompt(details)
    
    try:
        # Send the prompt to the Gemini model
        response = model.generate_content(prompt)
        
        # Clean up the response to ensure it's valid JSON
        # The AI can sometimes wrap the JSON in markdown backticks
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        print("--- Gemini Raw Response ---")
        print(cleaned_response_text)
        print("---------------------------")

        # Parse the JSON string from the AI's response
        itinerary_data = json.loads(cleaned_response_text)
        
        # Validate the data against our Pydantic model
        # This ensures the AI's output matches our required structure.
        itinerary = Itinerary(**itinerary_data)
        return itinerary

    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Error processing AI response: {e}")
        # If the AI response is not valid JSON or doesn't match our model, return an error.
        raise HTTPException(
            status_code=500, 
            detail="Failed to process the itinerary from the AI. The response was not in the expected format."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Catch any other potential errors (e.g., API connection issues)
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred while generating the itinerary: {str(e)}"
        )


@app.get("/")
def read_root():
    return {"message": "Welcome to the TripsAI API. Visit /docs for documentation."}

