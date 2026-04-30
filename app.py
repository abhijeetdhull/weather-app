from flask import Flask, request, render_template_string
import requests, mysql.connector
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
API_KEY = "2f43bef29fe13608bb8ecd38a0320c8b"
DB_CONFIG = dict(host="localhost", user="root", password="password", database="weather_app")

INDIAN_CAPITALS = [
    "Amaravati","Itanagar","Dispur","Patna","Raipur","Panaji","Gandhinagar","Chandigarh","Shimla","Ranchi",
    "Bengaluru","Thiruvananthapuram","Bhopal","Mumbai","Imphal","Shillong","Aizawl","Kohima","Bhubaneswar",
    "Jaipur","Gangtok","Chennai","Hyderabad","Agartala","Lucknow","Dehradun","Kolkata","Delhi","Port Blair",
    "Daman","Kavaratti","Puducherry","Leh","Srinagar"
]

def insert_weather(city, temp, humidity, pressure, wind, date):
    conn = mysql.connector.connect(**DB_CONFIG)
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

scheduler = BackgroundScheduler(); scheduler.add_job(collect_weather, 'interval', days=1); scheduler.start()

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Weather App</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f4f8; margin: 0; padding: 20px; }
        h1 { color: #2c3e50; text-align: center; }
        form { text-align: center; margin: 20px; }
        input, button { padding: 10px; margin: 5px; border-radius: 5px; border: 1px solid #ccc; }
        button { background: #3498db; color: white; border: none; cursor: pointer; }
        button:hover { background: #2980b9; }
        .weather-box { background: white; padding: 20px; margin: 20px auto; width: 400px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
        a { text-decoration: none; color: #3498db; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>🌤 Weather Checker</h1>
    <form method="post">
        <input type="text" name="city" placeholder="Enter city..." required>
        <button type="submit">Get Weather</button>
    </form>

    {% if w %}
    <div class="weather-box">
        <h2>{{ w.city }}</h2>
        <p><strong>Temperature:</strong> {{ w.temp }} °C</p>
        <p><strong>Humidity:</strong> {{ w.humidity }} %</p>
        <p><strong>Pressure:</strong> {{ w.pressure }} hPa</p>
        <p><strong>Wind Speed:</strong> {{ w.wind }} m/s</p>
    </div>
    {% endif %}

    <p style="text-align:center;">
        <a href="/history">📜 View History</a> | 
        <a href="/history_chart">📊 Multi-City Chart</a>
    </p>
</body>
</html>
"""

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
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT date, city, temperature, humidity, pressure, wind_speed FROM weather_data ORDER BY date DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    html = """
<!doctype html>
<html>
<head>
    <title>Weather History</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f9fafc; padding: 20px; }
        h1 { text-align: center; color: #2c3e50; }
        table { width: 90%; margin: auto; border-collapse: collapse; background: white; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
        th, td { padding: 10px; text-align: center; border-bottom: 1px solid #ddd; }
        th { background: #3498db; color: white; }
        tr:hover { background: #f1f1f1; }
        a { display: block; text-align: center; margin-top: 20px; color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>📜 Weather History</h1>
    <table>
        <tr>
            <th>Date</th><th>City</th><th>Temp</th><th>Humidity</th><th>Pressure</th><th>Wind</th>
        </tr>
        {% for r in rows %}
        <tr>
            <td>{{ r[0] }}</td><td>{{ r[1] }}</td><td>{{ r[2] }}</td>
            <td>{{ r[3] }}</td><td>{{ r[4] }}</td><td>{{ r[5] }}</td>
        </tr>
        {% endfor %}
    </table>
    <a href="/">⬅ Back to Search</a>
</body>
</html>
"""

    return render_template_string(html, rows=rows)


@app.route("/forecast/<city>")
def forecast(city):
    conn=mysql.connector.connect(**DB_CONFIG); cur=conn.cursor()
    cur.execute("SELECT date,temperature FROM weather_data WHERE city=%s AND date>=CURDATE()-INTERVAL 5 DAY ORDER BY date",(city,))
    past=cur.fetchall(); cur.close(); conn.close()
    fut=[(i["dt_txt"].split()[0],i["main"]["temp"]) for i in requests.get(
        f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric").json().get("list",[])]
    cutoff=datetime.now().date()+timedelta(days=5)
    fut=[(d,t) for d,t in fut if datetime.strptime(d,"%Y-%m-%d").date()<=cutoff]
    dates=[str(d) for d,_ in past]+[d for d,_ in fut]; temps=[t for _,t in past]+[t for _,t in fut]
    return render_template_string("""<h1>10-Day Forecast for {{city}}</h1><canvas id=c></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>
    new Chart(document.getElementById('c'),{type:'line',data:{labels:{{dates|tojson}},
    datasets:[{label:'Temp °C',data:{{temps|tojson}},borderColor:'blue',fill:false}]}});</script>
    <p><a href="/">Back</a></p>""",city=city,dates=dates,temps=temps)

@app.route("/history_chart")
def history_chart():
    conn=mysql.connector.connect(**DB_CONFIG); cur=conn.cursor()
    cur.execute("SELECT date,city,temperature FROM weather_data ORDER BY date"); rows=cur.fetchall()
    cur.close(); conn.close()
    data={}; 
    for d,c,t in rows: data.setdefault(c,{"dates":[],"temps":[]}); data[c]["dates"].append(str(d)); data[c]["temps"].append(t)
    all_dates=sorted(set(d for d,_,_ in rows))
    return render_template_string("""<h1>Multi-City Chart</h1><canvas id=mc></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>
    new Chart(document.getElementById('mc'),{type:'line',data:{labels:{{all_dates|tojson}},datasets:[
    {% for city,data in data.items() %}{label:'{{city}}',data:{{data.temps|tojson}},borderColor:'#'+Math.floor(Math.random()*16777215).toString(16),fill:false},{% endfor %}]}});</script>
    <p><a href="/">Back</a></p>""",data=data,all_dates=all_dates)

if __name__=="__main__": app.run(debug=True)
