from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import subprocess  # To start Streamlit programmatically
import os  # For working with file paths
from mood_track import load_resources, detect_emotion
from datetime import datetime


app = Flask(__name__)

model, tokenizer = load_resources()

# Configuring Flask App
app.secret_key = 'iamironman'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'ARYA#305#varun'
app.config['MYSQL_DB'] = 'emotion_recommendations'

mysql = MySQL(app)


# Route for Main Page (Page 1)
@app.route('/')
@app.route('/mainpage')
def mainpage():
    if 'loggedin' in session:
        return render_template('mainpage.html', username=session['username'])
    else:
        return render_template('mainpage.html')


@app.route('/detect_emotion', methods=['GET', 'POST'])
def moodtracker():
    if request.method == 'POST':
        data = request.get_json()
        input_text = data.get('input_text')

        # Predict the emotion
        emotion, prediction = detect_emotion(input_text, model, tokenizer)

        # Fetch recommendations from the database
        cursor = mysql.connection.cursor()

        timestamp = datetime.now()
        
        id = session['id']  # Get the user ID from the session
        cursor.execute("UPDATE accounts SET mood = %s WHERE id = %s", (emotion, id))
        cursor.execute("INSERT INTO emotion_log(user_id,emotion,timestamp) VALUES (%s , %s, %s)",(id, emotion,timestamp))
        mysql.connection.commit()

        cursor.execute("SELECT title FROM movies WHERE emotion = %s ORDER BY RAND() LIMIT 3", (emotion,))
        movie_recommendation = cursor.fetchall()

        cursor.execute("SELECT song, artist FROM music WHERE emotion = %s ORDER BY RAND() LIMIT 3", (emotion,))
        music_recommendation = cursor.fetchall()

        cursor.execute("SELECT activity FROM exercises WHERE emotion = %s ORDER BY RAND() LIMIT 3", (emotion,))
        exercise_recommendation = cursor.fetchall()

        # Prepare the recommendations
        recommendations = {
            'emotion': emotion,
            'movies': movie_recommendation if movie_recommendation else ['No movie found'],
            'music': music_recommendation if music_recommendation else ['No music found'],
            'exercises': exercise_recommendation if exercise_recommendation else ['No exercise found']
        }

        # Return the recommendations as JSON
        return jsonify(recommendations)
    else:
        return render_template('mood_track.html')
 




# Route for Login Page (Page 2)
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE email = %s AND password = %s', (email, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']  # Store email in session
            print("Login successful, redirecting to mainpage...")
            return redirect(url_for('mainpage'))
        else:
            msg = 'Incorrect email / password!'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to the login page
    return redirect(url_for('mainpage'))


# Route for Signup Page  (Page 3)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return redirect(url_for('login'))  # Redirect to login after successful registration
    return render_template('signup.html', msg=msg)


# Route for Chatbot  Page  (Page 4)

@app.route('/chatbot')
def chatbot():
    # Path to your Streamlit script
    streamlit_script = os.path.join(os.getcwd(), 'streamlit_ui.py')
    
    # Launch Streamlit as a subprocess
    subprocess.Popen(["streamlit", "run", streamlit_script])

    # Redirect to the Streamlit app once it's running
    streamlit_url = "http://localhost:8501"
    return redirect(streamlit_url)


# Route for Diary Entry Submission   (Page 5)
# Route for Diary Entry Submission (Page 5)
@app.route('/diary_entry', methods=['GET', 'POST'])
def diary_entry():
    if 'loggedin' in session:
        msg = ''
        if request.method == 'POST':
            entry_title = request.form['entry_title']
            entry_date = request.form['entry_date']
            entry_time = request.form['entry_time']
            entry_text = request.form['entry_text']
            
            # Validate form inputs
            if not entry_title or not entry_date or not entry_time or not entry_text:
                msg = 'Please fill out all fields!'
            else:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(
                    'INSERT INTO diary_entries (user_id, entry_title, entry_date, entry_time, entry_text) VALUES (%s, %s, %s, %s, %s)',
                    (session['id'], entry_title, entry_date, entry_time, entry_text))
                mysql.connection.commit()
                msg = 'Diary entry added successfully!'
                return redirect(url_for('diary'))  # Redirect to diary display after adding
        return render_template('di.html', msg=msg)
    return redirect(url_for('login'))


# Route for displaying diary entries (Page 6)
@app.route('/diary')
def diary():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT entry_title, entry_date, entry_time, entry_text FROM diary_entries WHERE user_id = %s ORDER BY entry_date DESC, entry_time DESC', (session['id'],))
        diary_entries = cursor.fetchall()
        return render_template('display_diary.html', diary_entries=diary_entries)
    return redirect(url_for('login'))

@app.route('/moodgraph')
def moodgraph():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT emotion, timestamp FROM emotion_log WHERE user_id = %s ORDER BY timestamp DESC', (session['id'],))
        mood_data = cursor.fetchall()

        print("Mood Data:", mood_data)  # Debug print statement

        # Check if mood_data is not empty
        if not mood_data:
            return "No mood data found."

        # Prepare data for chart
        emotions = [entry['emotion'] for entry in mood_data][::-1]  # Reverse the emotions
        timestamps = [entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S") for entry in mood_data][::-1]  # Reverse the timestamps

        print("Emotions:", emotions)  # Debug print statement
        print("Timestamps:", timestamps)  # Debug print statement

        return render_template('moodgraph.html', emotions=emotions, timestamps=timestamps)
    else:
        return redirect(url_for('login'))





if __name__ == '__main__':
    app.run(port=5000, debug=True)

