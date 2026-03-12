import requests

# --- Config ---
API_KEY = ""  # <-- Replace with your actual OpenWeatherMap API key
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str) -> str:
    """Fetch weather for a city and return a formatted string."""
    weather_url = f"{WEATHER_BASE_URL}?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(weather_url)

    if response.status_code == 200:
        data = response.json()
        temperature = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"]
        return (
            f"\n--- Weather Report ---\n"
            f"City        : {city.title()}\n"
            f"Temperature : {temperature}°C\n"
            f"Condition   : {description.capitalize()}\n"
            f"Humidity    : {humidity}%\n"
            f"{'─' * 30}"
        )
    else:
        return "\n❌ Could not retrieve weather. Please check the city name or API key."


def main():
    print("\n⛅  Welcome to the Weather Chatbot!")
    print("─" * 35)

    while True:
        city = input("\n🌍 Enter city name: ").strip()

        if not city:
            print("⚠️  City name cannot be empty. Please try again.")
            continue

        print(get_weather(city))

        while True:
            choice = input("\n🔄 Would you like to check another city? (yes/no): ").strip().lower()
            if choice in ("yes", "y"):
                break
            elif choice in ("no", "n"):
                print("\n👋 Thanks for using Weather Chatbot. Have a great day!\n")
                return
            else:
                print("⚠️  Please type 'yes' or 'no'.")


if __name__ == "__main__":
    main()