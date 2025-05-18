from flask import Flask, render_template, request, jsonify
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd  # Import pandas to work with dates
import mysql.connector
import base64
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# Define event types globally to ensure they appear in the plot even if counts are 0
ALL_EVENT_TYPES = ['Workshop', 'Webinar', 'Conference', 'FDP', 'Seminar', 'Hackathon']

# Function to connect to the SQL database
def connect_db():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",    # Replace with your SQL username
            password="password",  # Replace with your SQL password 
            database="Student_details"
        )
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Function to fetch event data based on roll number, mode, and date range
def fetch_student_data(roll_no=None, mode=None, start_date=None, end_date=None):
    db = connect_db()
    if db is None:
        return {}, {}

    cursor = db.cursor()

    # Construct the query based on roll_no, mode, and date range
    query = """
        SELECT type_of_event, COUNT(*) AS event_count, from_date
        FROM student 
        WHERE 1=1
    """
    
    params = []

    if roll_no and roll_no != 'all':
        query += " AND roll_no = %s"
        params.append(roll_no)

    if mode and mode.lower() != 'both':
        query += " AND mode = %s"
        params.append(mode)

    if start_date:
        query += " AND from_date >= %s"
        params.append(start_date)

    if end_date:
        query += " AND to_date <= %s"
        params.append(end_date)

    query += " GROUP BY type_of_event, from_date"
    
    cursor.execute(query, params)
    
    result = cursor.fetchall()
    db.close()

    # Create a dictionary with all event types initialized to 0
    event_data = {event: 0 for event in ALL_EVENT_TYPES}

    # Fill in the event counts from the database
    for event_type, count, _ in result:  # Ignore from_date here
        if event_type in ALL_EVENT_TYPES:
            event_data[event_type] += count

    return event_data

# Function to plot event data and return the image as a base64 string
def plot_event_data(data, roll_no=None):
    types_of_events = list(data.keys())
    counts = list(data.values())

    # Convert counts to a numpy array and replace NaN with 0
    counts = np.array(counts)
    counts = np.nan_to_num(counts)  # Replace NaNs with 0

    # Check for zero counts and adjust types_of_events accordingly
    if np.all(counts == 0):
        print("All counts are zero. Cannot plot.")
        return None

    # Assign different colors for each type of event
    colors = plt.cm.get_cmap('tab10', len(types_of_events)).colors

    # Create a figure with three subplots: bar, pie, and line
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))

    # Bar plot
    x_pos = np.arange(len(types_of_events))
    ax1.bar(x_pos, counts, align='center', color=colors)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(types_of_events, rotation=45, ha='right')

    if roll_no:
        ax1.set_title(f'Event Participation for Student: {roll_no}')
    else:
        ax1.set_title('Event Participation for All Students')

    ax1.set_ylabel('Number of Events')
    ax1.set_xlabel('Type of Event')

    # Pie chart
    # Filter out zero counts and their corresponding labels
    non_zero_counts = counts[counts > 0]
    non_zero_events = [types_of_events[i] for i in range(len(counts)) if counts[i] > 0]

    wedges, texts, autotexts = ax2.pie(non_zero_counts, labels=non_zero_events, autopct='%1.1f%%', colors=colors[:len(non_zero_events)], startangle=140)
    ax2.axis('equal')  # Equal aspect ratio ensures that pie chart is circular.
    ax2.set_title('Event Participation Distribution')

    # Adjust label properties to avoid overlapping
    plt.setp(texts, size=10, weight="bold")
    plt.setp(autotexts, size=10, weight="bold", color="white")


    # Line graph
    ax3.plot(types_of_events, counts, marker='o', linestyle='-', color='blue')
    ax3.set_title('Event Participation Trend')
    ax3.set_ylabel('Number of Events')
    ax3.set_xlabel('Type of Event')

    plt.tight_layout()
    
    # Convert plot to PNG image and encode it as base64
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    return img_base64


# Route for initial page load (with default plot for 'all', 'Both', and current date)
@app.route('/')
def index():
    # Create a blank plot with zero counts for each event type
    data = {event: 0 for event in ALL_EVENT_TYPES}
    
    # Generate a blank plot
    plot_url = plot_event_data(data, roll_no='all')
    
    return render_template('index.html', plot_url=plot_url)

# Route for updating the plot dynamically based on user input
@app.route('/update_plot', methods=['POST'])
def update_plot():
    roll_no = request.form.get('roll_no')
    mode = request.form.get('mode')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    try:
        data = fetch_student_data(roll_no=roll_no, mode=mode, start_date=start_date, end_date=end_date)
        plot_url = plot_event_data(data, roll_no=None if roll_no == 'all' else roll_no)
        return jsonify({'plot_url': plot_url})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
