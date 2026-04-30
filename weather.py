import requests
import psycopg2
from datetime import datetime
import os

# Read API key and DB config from environment variables
API_KEY = os.getenv("API_KEY")

DB_CONFIG = dict(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def insert_weather_data(city):
    """Fetch weather for a city and insert into DB if not already present for today."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        temp = data['main']['temp']
        humidity = data['main']['humidity']
        pressure = data['main']['pressure']
        wind = data['wind']['speed']
        date = datetime.now().strftime("%Y-%m-%d")

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Avoid duplicate for same city/date
            cursor.execute("SELECT COUNT(*) FROM weather_data WHERE date=%s AND city=%s", (date, city))
            if cursor.fetchone()[0] == 0:
                print("Inserting:", date, city, temp, humidity, pressure, wind)
                cursor.execute("""
                    INSERT INTO weather_data (date, city, temperature, humidity, pressure, wind_speed)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (date, city, temp, humidity, pressure, wind))
                conn.commit()
                print("Data inserted successfully!")
            else:
                print(f"Data for {city} on {date} already exists. Skipping insert.")

            cursor.close()
            conn.close()
        except Exception as e:
            print("Insert failed:", e)
    else:
        print("API error:", response.status_code, response.text)

# Run directly for testing
if __name__ == "__main__":
    insert_weather_data("Delhi")
