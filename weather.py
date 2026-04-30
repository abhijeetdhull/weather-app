import requests
import mysql.connector
from datetime import datetime

API_KEY = "2f43bef29fe13608bb8ecd38a0320c8b"
city = "Delhi"
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
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="your_password",
            database="weather_app"
        )
        cursor = conn.cursor()

        print("Inserting:", date, city, temp, humidity, pressure, wind)

        cursor.execute("""
        INSERT INTO weather_data (date, city, temperature, humidity, pressure, wind_speed)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (date, city, temp, humidity, pressure, wind))

        conn.commit()
        print("Data inserted successfully!")

        cursor.close()
        conn.close()
    except Exception as e:
        print("Insert failed:", e)
else:
    print("API error:", response.status_code, response.text)
