from flask import Flask, request, render_template_string
import requests, psycopg2
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import os

app = Flask(__name__)
API_KEY = os.getenv("API_KEY")  # now read from environment

DB_CONFIG = dict(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

INDIAN_CAPITALS = [
    "Amaravati","Itanagar","Dispur","Patna","Raipur","Panaji","Gandhinagar","Chandigarh","Shimla","Ranchi",
    "Bengaluru","Thiruvananthapuram","Bhopal","Mumbai","Imphal","Shillong","Aizawl","Kohima","Bhubaneswar",
    "Jaipur","Gangtok","Chennai","Hyderabad","Agartala","Lucknow","Dehradun","Kolkata","Delhi","Port Blair",
    "Daman","Kavaratti","Puducherry","Leh","Srinagar"
]

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def insert_weather(city, temp, humidity, pressure, wind, date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM weather_data WHERE date=%s AND city=%s", (date, city))
    if cur.fetchone()[0] == 0:
        cur.execute("""INSERT INTO weather_data (date, city, temperature, humidity, pressure, wind_speed)
                       VALUES (%s,%s,%s,%s,%s,%s)""", (date, city, temp, humidity, pressure, wind))
        conn.commit()
    cur.close(); conn.close()

def collect_weather():
    for city in INDIAN_CAPITALS:
        data = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric").json()
        if "main" in data:
            insert_weather(city, data['main']['temp'], data['main']['humidity'],
                           data['main']['pressure'], data['wind']['speed'],
                           datetime.now().strftime("%Y-%m-%d"))

scheduler = BackgroundScheduler()
scheduler.add_job(collect_weather, 'interval', days=1)
scheduler.start()

HTML_TEMPLATE = """ ... (unchanged HTML for index page) ... """

@app.route("/", methods=["GET","POST"])
def index():
    w=None
    if request.method=="POST":
        city=request.form["city"]
        data=requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric").json()
        if "main" in data:
            w=dict(city=city,temp=data['main']['temp'],humidity=data['main']['humidity'],
                   pressure=data['main']['pressure'],wind=data['wind']['speed'])
            insert_weather(city,w["temp"],w["humidity"],w["pressure"],w["wind"],datetime.now().strftime("%Y-%m-%d"))
    return render_template_string(HTML_TEMPLATE,w=w)

@app.route("/history")
def history():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT date, city, temperature, humidity, pressure, wind_speed FROM weather_data ORDER BY date DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()

    html = """ ... (unchanged HTML for history page) ... """
    return render_template_string(html, rows=rows)

@app.route("/forecast/<city>")
def forecast(city):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT date, temperature FROM weather_data WHERE city=%s AND date >= CURRENT_DATE - INTERVAL '5 days' ORDER BY date", (city,))
    past = cur.fetchall()
    cur.close(); conn.close()

    fut = [(i["dt_txt"].split()[0], i["main"]["temp"]) for i in requests.get(
        f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric").json().get("list",[])]
    cutoff = datetime.now().date() + timedelta(days=5)
    fut = [(d,t) for d,t in fut if datetime.strptime(d,"%Y-%m-%d").date() <= cutoff]

    dates = [str(d) for d,_ in past] + [d for d,_ in fut]
    temps = [t for _,t in past] + [t for _,t in fut]

    return render_template_string("""<h1>10-Day Forecast for {{city}}</h1><canvas id=c></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>
    new Chart(document.getElementById('c'),{type:'line',data:{labels:{{dates|tojson}},
    datasets:[{label:'Temp °C',data:{{temps|tojson}},borderColor:'blue',fill:false}]}});</script>
    <p><a href="/">Back</a></p>""",city=city,dates=dates,temps=temps)

@app.route("/history_chart")
def history_chart():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT date, city, temperature FROM weather_data ORDER BY date")
    rows = cur.fetchall()
    cur.close(); conn.close()

    data={}
    for d,c,t in rows:
        data.setdefault(c,{"dates":[],"temps":[]})
        data[c]["dates"].append(str(d))
        data[c]["temps"].append(t)
    all_dates = sorted(set(d for d,_,_ in rows))

    return render_template_string("""<h1>Multi-City Chart</h1><canvas id=mc></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>
    new Chart(document.getElementById('mc'),{type:'line',data:{labels:{{all_dates|tojson}},datasets:[
    {% for city,data in data.items() %}{label:'{{city}}',data:{{data.temps|tojson}},borderColor:'#'+Math.floor(Math.random()*16777215).toString(16),fill:false},{% endfor %}]}});</script>
    <p><a href="/">Back</a></p>""",data=data,all_dates=all_dates)

if __name__=="__main__":
    app.run(debug=True)
