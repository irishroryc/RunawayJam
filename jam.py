import os
from flask import abort, Flask, jsonify, request
import requests
import random
import logging

app = Flask(__name__)

DOT_NET_API_KEY = os.environ['DOT_NET_API_KEY']
PHISHIN_API_KEY = os.environ['PHISHIN_API_KEY']
PHISHIN_HEADERS = {'Authorization':'Bearer '+PHISHIN_API_KEY, 'Accept':'application/json'}
PHISHIN_LOGO = "http://phish.in/assets/logo-text-dcfa821a4529a5e9e377dd8f6f1a6b164d8f851fdefa89d9c321b34aa38828e7.png"

song_map = {}

def is_request_valid(request):
    is_token_valid = request.form['token'] == os.environ['SLACK_VERIFICATION_TOKEN']
    is_team_id_valid = request.form['team_id'] == os.environ['SLACK_TEAM_ID']

    if not is_team_id_valid:
        is_token_valid = request.form['token'] == os.environ['VISCO_TOKEN']
        is_team_id_valid = request.form['team_id'] == os.environ['VISCO_TEAM_ID']

    print("token_valid = ",is_token_valid)
    print("team_valid = ",is_team_id_valid)

    return is_token_valid and is_team_id_valid

def update_song_map():
    all_req = requests.get(url="https://api.phish.net/v3/jamcharts/all?apikey="+DOT_NET_API_KEY)
    all_dict = all_req.json()
    for jamsong in all_dict['response']['data']:
        slug = jamsong['link'].split('/')[-1]
        song_map[slug] = jamsong['songid']

def get_jam_date(song_id):
    jam_url = "https://api.phish.net/v3/jamcharts/get?songid="+str(song_id)+"&apikey="+DOT_NET_API_KEY
    jam_req = requests.get(url=jam_url)
    #print("DEBUG: ",jam_req.json())
    jam_req_dict = jam_req.json()['response']['data']['entries']
    random_choice = random.randint(0,len(jam_req_dict))
    return jam_req_dict[random_choice]['showdate']

def get_venue(show_id):
    show_req = requests.get(url="http://phish.in/api/v1/shows/"+str(show_id)+".json", 
                            headers=PHISHIN_HEADERS)
    show_data = show_req.json()
    return show_data['data']['venue']['name']

@app.route('/jam', methods=['POST'])
def jam():
    if not is_request_valid(request):
        abort(400)

    if request.form['text']:
        PHISHIN_SONG = request.form['text']
        CLEAN_SONG = PHISHIN_SONG.replace(' ','-').lower()
        PHISHIN_URL = "http://phish.in/api/v1/songs/"+CLEAN_SONG+".json"
    else:
        return jsonify(
            response_type='in_channel',
            text="Sorry, couldn't find that song. Go Phish!",
        )

    #print("PHISHIN_URL = ",PHISHIN_URL)
    #print("PHISHIN_HEADERS = ",PHISHIN_HEADERS)
    r = requests.get(url = PHISHIN_URL, headers=PHISHIN_HEADERS)

    if r.status_code == 404:
        return jsonify(
            response_type='in_channel',
            text="Sorry, couldn't find that song. Go Phish!",
        )

    update_song_map()

    if CLEAN_SONG in song_map:
        jam_song_id = song_map[CLEAN_SONG]
    else:
        return jsonify(
            response_type='in_channel',
            text="No jamchart entry for "+PHISHIN_SONG+", that song suuucks! (Go Phish!)",
        ) 

    jam_date = get_jam_date(jam_song_id)

    #print("r.cookies = ",r.cookies)
    #print("r.headers = ",r.headers)
    #print("r.text = ",r.text)
    data = r.json()

    jam_tracks = data['data']['tracks']
    for jam in jam_tracks:
        if jam['show_date'] == jam_date:
            track = jam
    #print("jam_track =",track)
    track_mp3 = track['mp3']
    track_date = track['show_date']
    track_set = track['set_name'].lower()
    track_venue = get_venue(track['show_id'])
    track_title = track_venue+"\n"+track_date
    track_link = "http://phish.in/"+track_date+"/"+CLEAN_SONG
    track_pretext = "Random Jamchart version of "+PHISHIN_SONG+" from "+track_venue
    track_notes = None
    for tags in track['tags']:
        if tags['notes'] is not None:
            track_notes = tags['notes']
    if track_notes == None:
        track_notes = "Check out this killer "+track_set+" "+PHISHIN_SONG+"!!"

    return jsonify(
        response_type='in_channel',
        text=track_pretext,
        attachments=[{'pretext':track_notes,'image_url':PHISHIN_LOGO,'title':track_title,'title_link':track_link}]
    )
