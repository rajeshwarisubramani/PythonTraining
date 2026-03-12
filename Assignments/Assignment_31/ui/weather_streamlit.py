import streamlit as st
import requests

# --- Config ---
API_KEY = "KEY"  # <-- Replace with your actual OpenWeatherMap API key
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
            f"🌍 **{city.title()}** Weather Report\n\n"
            f"🌡️ **Temperature:** {temperature}°C\n\n"
            f"🌤️ **Condition:** {description.capitalize()}\n\n"
            f"💧 **Humidity:** {humidity}%"
        )
    else:
        return f"❌ Could not retrieve weather for **{city}**. Please check the city name or API key."


# --- Page Setup ---
st.set_page_config(page_title="Weather Chatbot", page_icon="⛅")
st.title("⛅ Weather Chatbot")

# --- Session State Init ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "stage" not in st.session_state:
    st.session_state.stage = "ask_city"  # Stages: ask_city | ask_continue | done

# --- Render chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Initial bot greeting ---
if st.session_state.stage == "ask_city" and not st.session_state.messages:
    greeting = "👋 Hello! I'm your Weather Bot. Which city would you like to check the weather for?"
    st.session_state.messages.append({"role": "assistant", "content": greeting})
    with st.chat_message("assistant"):
        st.markdown(greeting)

# --- Input box (hidden when done) ---
if st.session_state.stage != "done":
    placeholder = (
        "Enter a city name..." if st.session_state.stage == "ask_city"
        else "Type 'yes' to continue or 'no' to exit..."
    )
    user_input = st.chat_input(placeholder)
else:
    user_input = None

# --- Handle user input ---
if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # --- Stage: asking for city ---
    if st.session_state.stage == "ask_city":
        weather_report = get_weather(user_input.strip())
        follow_up = "Would you like to check another city? Type **yes** to continue or **no** to exit."
        bot_reply = f"{weather_report}\n\n---\n{follow_up}"
        st.session_state.stage = "ask_continue"

    # --- Stage: asking to continue ---
    elif st.session_state.stage == "ask_continue":
        answer = user_input.strip().lower()
        if answer in ("yes", "y"):
            bot_reply = "Great! Which city would you like to check next?"
            st.session_state.stage = "ask_city"
        elif answer in ("no", "n"):
            bot_reply = "👋 Thanks for using Weather Bot. Have a great day!"
            st.session_state.stage = "done"
        else:
            bot_reply = "I didn't quite catch that. Please type **yes** to continue or **no** to exit."

    # Show bot reply
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    with st.chat_message("assistant"):
        st.markdown(bot_reply)

    st.rerun()

# --- Done state UI ---
if st.session_state.stage == "done":
    if st.button("🔄 Start Over"):
        st.session_state.messages = []
        st.session_state.stage = "ask_city"
        st.rerun()