from flask import Flask, render_template, request

app = Flask(__name__)

# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Result page (AI logic)
@app.route('/result', methods=['POST'])
def result():
    traffic = request.form['traffic']
    air = request.form['air']

    # AI Logic (Decision Engine)
    if traffic == "high" and air == "poor":
        suggestion = "🚫 Avoid travel. Use public transport and wear a mask."
    elif traffic == "high":
        suggestion = "⚠️ Heavy traffic. Consider alternate routes."
    elif    air == "poor":
        suggestion = "😷 Air quality is poor. Wear a mask."
    elif traffic == "low" and air == "good":
        suggestion = "✅ Safe to travel."
    else:
        suggestion = "⚡ Moderate conditions. Travel carefully."

    return render_template('result.html',
                           traffic=traffic,
                           air=air,
                           suggestion=suggestion)

if __name__ == '__main__':
    app.run(debug=True)