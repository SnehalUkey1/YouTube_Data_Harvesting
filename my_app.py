from tkinter import Tk, Label, Button, Entry, StringVar, OptionMenu
from googleapiclient.discovery import build
from pymongo import MongoClient

api_key = 'AIzaSyAYVUhxzm77Va3d7lmkCdMQKQA3UnQP2rU'

youtube = build('youtube', 'v3', developerKey=api_key)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['youtube_data']
channel_collection = db['channels']
video_collection = db['videos']

def get_channel_data(channel_id):
    request = youtube.channels().list(
        part='snippet,contentDetails,statistics',
        id=channel_id
    )
    response = request.execute()

    if 'items' in response:
        channel_data = response['items'][0]
        channel_name = channel_data['snippet']['title']
        subscribers = channel_data['statistics']['subscriberCount']
        total_videos = channel_data['statistics']['videoCount']
        playlist_id = channel_data['contentDetails']['relatedPlaylists']['uploads']

        video_data = []
        next_page_token = None

        while True:
            playlist_request = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            playlist_response = playlist_request.execute()

            for item in playlist_response['items']:
                video_id = item['snippet']['resourceId']['videoId']
                video_request = youtube.videos().list(
                    part='statistics',
                    id=video_id
                )
                video_response = video_request.execute()

                if 'items' in video_response:
                    video_stats = video_response['items'][0]['statistics']
                    likes = video_stats.get('likeCount', 0)
                    dislikes = video_stats.get('dislikeCount', 0)
                    comments = video_stats.get('commentCount', 0)

                    video_data.append({
                        'video_id': video_id,
                        'likes': likes,
                        'dislikes': dislikes,
                        'comments': comments
                    })

            next_page_token = playlist_response.get('nextPageToken')

            if not next_page_token:
                break

        return {
            'channel_name': channel_name,
            'subscribers': subscribers,
            'total_videos': total_videos,
            'playlist_id': playlist_id,
            'video_data': video_data
        }
    else:
        return None
    
def collect_data():
    # Retrieve input values
    channel_ids = [entry.get() for entry in channel_entries]
    
    for channel_id in channel_ids:
        channel_data = get_channel_data(channel_id)
        
        if channel_data:
            # Store the channel data in MongoDB
            channel_collection.insert_one(channel_data)
            print("Channel data stored in MongoDB.")
        
            # Store the video data in MongoDB
            video_collection.insert_many(channel_data['video_data'])
            print("Video data stored in MongoDB.")
        
        else:
            print(f"Channel with ID {channel_id} not found or an error occurred.")
            
# GUI Setup
root = Tk()
root.title("YouTube Data Collection")

# Channel ID Input
label = Label(root, text="Enter YouTube Channel IDs (up to 10):")
label.pack()

channel_entries = []
for _ in range(10):
    entry = Entry(root)
    entry.pack()
    channel_entries.append(entry)

# Collect Data Button
button = Button(root, text="Collect Data", command=collect_data)
button.pack()

root.mainloop()

import mysql.connector
from tkinter import Tk, Label, Button, Entry, StringVar, OptionMenu

# SQL Database connection
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='12345',
    database='guvi'
)
cursor = conn.cursor()


def migrate_data():
    # Retrieve the selected channel name and ID from the dropdown menu
    selected_channel_name = selected_channel.get()
    selected_channel_id = channel_ids[selected_channel_name]

    # Retrieve channel data from the MongoDB
    channel_data = channel_collection.find_one({'channel_name': selected_channel_name})

    if channel_data:
        try:
            # Create channel table if it doesn't exist
            create_channel_table_query = "CREATE TABLE IF NOT EXISTS channels (channel_id INT AUTO_INCREMENT PRIMARY KEY, channel_name VARCHAR(255), subscribers INT, total_videos INT, playlist_id VARCHAR(255));"
            cursor.execute(create_channel_table_query)

            # Insert channel data into the SQL table
            insert_channel_data_query = "INSERT INTO channels (channel_name, subscribers, total_videos, playlist_id) VALUES (%s, %s, %s, %s);"
            channel_values = (channel_data['channel_name'], channel_data['subscribers'], channel_data['total_videos'], channel_data['playlist_id'])
            cursor.execute(insert_channel_data_query, channel_values)

            # Create video table for the selected channel if it doesn't exist
            create_video_table_query = f"CREATE TABLE IF NOT EXISTS videos_{selected_channel_id} (video_id VARCHAR(255), likes INT, dislikes INT, comments INT);"
            cursor.execute(create_video_table_query)

            # Retrieve video data from the MongoDB
            video_data = video_collection.find({'video_id': {'$in': [video['video_id'] for video in channel_data['video_data']]}})
            
            # Insert video data into the SQL table for the selected channel
            for video in video_data:
                video_values = (video['video_id'], video['likes'], video['dislikes'], video['comments'])
                insert_video_data_query = f"INSERT INTO videos_{selected_channel_id} (video_id, likes, dislikes, comments) VALUES (%s, %s, %s, %s);"
                cursor.execute(insert_video_data_query, video_values)

            # Commit the changes to the SQL database
            conn.commit()
            print("Data migration completed successfully.")
        except Exception as e:
            print(f"An error occurred during data migration: {str(e)}")
    else:
        print(f"Channel '{selected_channel_name}' not found in the MongoDB.")

# GUI Setup
root = Tk()
root.title("YouTube Data Migration")

# Channel Name Selection
label = Label(root, text="Select YouTube Channel Name:")
label.pack()

channel_names = [channel['channel_name'] for channel in channel_collection.find()]
channel_ids = {channel['channel_name']: channel['_id'] for channel in channel_collection.find()}
selected_channel = StringVar(root)
selected_channel.set('KrsihNaik')  # Set the default selected channel

channel_dropdown = OptionMenu(root, selected_channel, *channel_names)
channel_dropdown.pack()

# Data Migration Button
button = Button(root, text="Migrate Data", command=migrate_data)
button.pack()

root.mainloop()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create the SQLAlchemy engine
engine = create_engine('mysql+mysqlconnector://root:password@localhost/guvi')

# Create a Session object to interact with the database
Session = sessionmaker(bind=engine)
session = Session()

def get_channel_data(channel_names):
    channel_data = []

    for channel_name in channel_names:
        channel = session.query(Channel).filter_by(channel_name=channel_name).first()

        if channel:
            videos = session.query(Video).filter_by(channel_id=channel.channel_id).all()

            channel_data.append({
                'channel_name': channel.channel_name,
                'subscribers': channel.subscribers,
                'total_videos': channel.total_videos,
                'playlist_id': channel.playlist_id,
                'videos': videos
            })

    return channel_data

def migrate_data():
    # Retrieve the selected channel names from the dropdown menu
    selected_channel_names = selected_channel.get()

    # Convert the string of selected channel names to a list
    selected_channel_names = selected_channel_names.split(",")

    # Retrieve channel data and video data for all the selected channels
    channel_data = get_channel_data(selected_channel_names)

    if channel_data:
        for data in channel_data:
            print("Channel Name:", data['channel_name'])
            print("Subscribers:", data['subscribers'])
            print("Total Videos:", data['total_videos'])
            print("Playlist ID:", data['playlist_id'])
            print("Videos:")
            for video in data['videos']:
                print("Video ID:", video.video_id)
                print("Likes:", video.likes)
                print("Dislikes:", video.dislikes)
                print("Comments:", video.comments)
                print()

        print("Data retrieval completed successfully.")
    else:
        print("No data found for the selected channels.")
    
# Channel Name Selection
label = Label(root, text="Select YouTube Channel Names (comma-separated):")
label.pack()

channel_dropdown = Entry(root)
channel_dropdown.pack()

# Data Migration Button
button = Button(root, text="Retrieve Data", command=migrate_data)
button.pack()
