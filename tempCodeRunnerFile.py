import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="your_password",
    database="weather_app"
)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM weather_data")
count = cursor.fetchone()[0]
print("Row count:", count)

cursor.close()
conn.close()

