import requests


API_KEY = ""  # <-- Replace this with your actual key
CITY = "Hyderabad"
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
GEO_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct"

# Construct the full API request URL
weather_url = f"{WEATHER_BASE_URL}?q={CITY}&appid={API_KEY}&units=metric"

print(weather_url)

# Send GET request
weather_response = requests.get(weather_url)



# Check if the request was successful
if weather_response.status_code == 200:
    weather_data = weather_response.json()

    # Extract specific information
    temperature = weather_data["main"]["temp"]
    humidity = weather_data["main"]["humidity"]
    description = weather_data["weather"][0]["description"]

    # Display in a user-friendly format
    print("\n--- Weather Report ---")
    print(f"City: {CITY}")
    print(f"Temperature: {temperature}°C")
    print(f"Weather: {description.capitalize()}")
    print(f"Humidity: {humidity}%")
    print("-" * 40)
else:
    print("\nFailed to retrieve weather data. Check API key or city name.")