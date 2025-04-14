from flask import Flask,render_template,url_for,request,jsonify,session,redirect,url_for,jsonify
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn import preprocessing, model_selection
from plotly.offline import plot
import pandas as pd
import datetime as dt
import numpy as np
import yfinance as yf
import sqlite3
import requests
import ta  # Technical analysis library
app=Flask(__name__)
app.secret_key = 'supersecretkey'


@app.route("/get_price/<ticker>")
def get_price(ticker):
    return str(get_real_time_price(ticker))

def get_stock_chart(ticker):
    ticker=ticker.upper()
    df = yf.download(ticker, period="6mo", interval="1d")
    df.columns = [col[0] for col in df.columns.values]

    if not ticker:
        return jsonify({'error': 'Stock symbol is required'}), 400


    if df.empty:
        return jsonify({'error': 'Invalid stock symbol or no data available'}), 404

    # Calculate indicators
    df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # MACD Calculation
    df['MACD'] = ta.trend.macd(df['Close'])
    df['MACD_Signal'] = ta.trend.macd_signal(df['Close'])

    # Create Candlestick Chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Market Data"))
    
    # Add Indicators
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], mode='lines', name='SMA 50', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], mode='lines', name='EMA 20', line=dict(color='orange')))
    
    # Layout
    fig.update_layout(title=f"{ticker} Stock Price & Indicators", yaxis_title="Stock Price (USD)", xaxis_rangeslider_visible=True, template="seaborn")
    

    return plot(fig, auto_open=False, output_type="div")


def get_real_time_price(ticker):
    try:
        print(ticker)
        stock = yf.Ticker(ticker)
        last_price = stock.history(period="1d")["Close"].iloc[-1]  # Get last closing price
        print(last_price)
        return round(last_price, 2)
    
    except Exception as e:
        print(f"Error fetching price data: {e}")
        return "Error Fetching Data"



def get_db_connection():
    try:
        conn = sqlite3.connect('mydb.db')
        cursor = conn.cursor()

        # Create the 'users' table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                datetime TEXT NOT NULL
            )
        ''')

        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection failed: {e}")
        return None

# def get_stock_chart(ticker):
#     # Fetch stock data
#     df = yf.download(ticker, period='1y', interval='1d')
#     fig = go.Figure()
#     fig.add_trace(go.Candlestick(x=df.index,
#                 open=df['Open'],
#                 high=df['High'],
#                 low=df['Low'],
#                 close=df['Close'], name = 'market data'))
#     fig.update_layout(
#                         title='{} live share price evolution'.format(ticker),
#                         yaxis_title='Stock Price (USD per Shares)')
#     fig.update_xaxes(
#     rangeslider_visible=True,
#     rangeselector=dict(
#         buttons=list([
#             dict(count=15, label="15m", step="minute", stepmode="backward"),
#             dict(count=45, label="45m", step="minute", stepmode="backward"),
#             dict(count=1, label="HTD", step="hour", stepmode="todate"),
#             dict(count=3, label="3h", step="hour", stepmode="backward"),
#             dict(step="all")
#         ])
#         )
#     )
#     fig.update_layout(paper_bgcolor="#14151b", plot_bgcolor="#14151b", font_color="white")
#     plot_div = plot(fig, auto_open=False, output_type='div')

#     return plot_div


@app.route('/',methods=["GET", "POST"])
def index():
    if 'user_id' in session:
        chart = None
        stock_symbol = "AAPL"  # Default stock
        chart = get_stock_chart(stock_symbol)
        if request.method == "POST":
            stock_symbol = request.form.get("stock_symbol", "AAPL").upper()
            print("stock_stock_",stock_symbol)
            chart=get_stock_chart(stock_symbol)
            stock = yf.Ticker(stock_symbol)
            stock_info = stock.info
            return render_template("hom.html", chart=chart,stock_symbol=stock_symbol,stock_info=stock_info)
        return render_template("hom.html", chart=chart,stock_symbol=stock_symbol)
    return render_template("index.html",)


@app.route('/predict',methods=["GET", "POST"])
def predict():
    if 'user_id' in session:
        if request.method == "POST":
            stock_symbol = request.form.get("stock_symbol", "AAPL").upper()
            number_of_days = request.form.get("number_of_days")
            number_of_days=int(number_of_days)
            print("stock_stock_",stock_symbol)
            chart=get_stock_chart(stock_symbol)
            stock = yf.Ticker(stock_symbol)
            stock_info = stock.info
            try:

                df_ml = yf.download(tickers=stock_symbol, period='3mo', interval='1h')
            except Exception as E:
                print(E)
                df_ml = yf.download(tickers='AAPL', period='3mo', interval='1h')
            df_ml.columns = [col[0] for col in df_ml.columns.values]
            df_ml = df_ml[['Close']]
            df_ml['Prediction'] = df_ml[['Close']].shift(-number_of_days)

            X = np.array(df_ml.drop(['Prediction'], axis=1))
            X = preprocessing.scale(X)
            X_forecast = X[-number_of_days:]
            X = X[:-number_of_days]
            y = np.array(df_ml['Prediction'])
            y = y[:-number_of_days]
            X_train, X_test, y_train, y_test = model_selection.train_test_split(X, y, test_size=0.2)

            clf = LinearRegression()
            clf.fit(X_train, y_train)
            confidence = clf.score(X_test, y_test)
            forecast_prediction = clf.predict(X_forecast)
            forecast = forecast_prediction.tolist()

            # Plotting predicted data
            pred_dict = {"Date": [], "Prediction": []}
            for i in range(0, len(forecast)):
                pred_dict["Date"].append(dt.datetime.today() + dt.timedelta(days=i))
                pred_dict["Prediction"].append(forecast[i])
            
            pred_df = pd.DataFrame(pred_dict)
            pred_fig = go.Figure([go.Scatter(x=pred_df['Date'], y=pred_df['Prediction'])])
            pred_fig.update_xaxes(rangeslider_visible=True)
            pred_fig.update_layout(template="seaborn")
            plot_div_pred = plot(pred_fig, auto_open=False, output_type='div')

            # Example DataFrame (replace with your own data)
            # pred_df = ...

            # Create a line chart with multiple series
            # line_fig = go.Figure()

            # # Adding multiple lines
            # line_fig.add_trace(go.Scatter(x=pred_df['Date'], y=pred_df['Prediction'], mode='lines', name='Predictions'))
            # # line_fig.add_trace(go.Scatter(x=pred_df['Date'], y=pred_df['Actual'], mode='lines', name='Actual Values'))

            # # Update x-axis with a range slider
            # line_fig.update_xaxes(rangeslider_visible=True)

            # # Apply a different template
            # line_fig.update_layout(template="seaborn")

            # # Render the plot as a div (for embedding into a webpage or dashboard)
            # plot_div_line = plot(line_fig, auto_open=False, output_type='div')


            return render_template("prediction.html", chart=chart,stock_symbol=stock_symbol,stock_info=stock_info,plot_div_pred=plot_div_pred)
        return redirect(url_for('index'))
    return render_template("index.html", )

    # stock_symbol = request.form.get("stock_symbol", "AAPL").upper()
    # chart = get_stock_chart()
    
    # news = get_stock_news(stock_symbol)
    # news_sentiment = analyze_sentiment(news)
    # return render_template("index.html", chart=chart)
    # return render_template("index.html", chart=chart, stock_symbol=stock_symbol)

@app.route('/prediction')
def prediction():
    if 'user_id' in session:
        return render_template('prediction.html')
    return render_template('index.html')

portfolio = {}

@app.route("/portfolio", methods=["GET", "POST"])
def portfolio_page():
    global portfolio
    if request.method == "POST":
        stock = request.form.get("stock_symbol").upper()
        shares = int(request.form.get("shares"))
        price = get_real_time_price(stock)
        if stock in portfolio:
            portfolio[stock]["shares"] += shares
        else:
            portfolio[stock] = {"shares": shares, "price": price}

    return render_template("portfolio.html", portfolio=portfolio)



@app.route('/register')
def register():

    return render_template('register.html')

@app.route('/add_user', methods=['POST'])
def add_user():
    try:
        from datetime import datetime
        username = request.form['name']
        print(username)
        email = request.form['email']
        password = request.form['password']
        datetime_now = datetime.now().isoformat()

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, email, password, datetime) VALUES (?, ?, ?, ?)',
                           (username, email, password, datetime_now))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
        else:
            return jsonify({'status': 'failed', 'error': 'Database connection failed'})
    except Exception as e:
        print(f"Error in add_user: {e}")
        return jsonify({'status': 'failed', 'error': str(e)})
    
def validate(username, password):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            conn.close()

            if user and user['password'] == password:
                return True, username
        return False, username
    except sqlite3.Error as e:
        print(f"Database error during validation: {e}")
        return False, username
    

@app.route('/verify_user', methods=['POST', 'GET'])
def login():
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            completion, username = validate(username, password)
            if completion:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
                    user = cursor.fetchone()
                    
                    conn.close()
                    

                    for i in user:
                        print("user",i)
                    if user:
                        
                        session['user_id'] = user['id']
                        session['user_name']=username
                        session['email']=user['email']
                        session['logged_in'] = True
                        return redirect(url_for('index'))
                return  render_template('index.html', error = 'User not found')
            return render_template('index.html', error = 'Invalid credentials')
        else:
            render_template('index.html')
    except Exception as E:
        # return redirect(url_for('index',error=E))
        return render_template('index.html',error=E)


@app.route('/new')
def new():

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__=='__main__':
    app.run(debug=True,port='5002')
