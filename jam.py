import os
from flask import abort, Flask, jsonify, request
import requests
import random
import logging

app = Flask(__name__)

PHISHIN_API_KEY = os.environ['PHISHIN_API_KEY']
PHISHIN_HEADERS = {'Authorization':'Bearer '+PHISHIN_API_KEY, 'Accept':'application/json'}
PHISHIN_LOGO = "http://phish.in/assets/logo-text-dcfa821a4529a5e9e377dd8f6f1a6b164d8f851fdefa89d9c321b34aa38828e7.png"

def is_request_valid(request):
    is_token_valid = request.form['token'] == os.environ['SLACK_VERIFICATION_TOKEN']
    is_team_id_valid = request.form['team_id'] == os.environ['SLACK_TEAM_ID']

    if not is_team_id_valid:
        is_token_valid = request.form['token'] == os.environ['VISCO_TOKEN']
        is_team_id_valid = request.form['team_id'] == os.environ['VISCO_TEAM_ID']

    print("token_valid = ",is_token_valid)
    print("team_valid = ",is_team_id_valid)

    return is_token_valid and is_team_id_valid

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

    print("PHISHIN_URL = ",PHISHIN_URL)
    print("PHISHIN_HEADERS = ",PHISHIN_HEADERS)
    r = requests.get(url = PHISHIN_URL, headers=PHISHIN_HEADERS)
    print("r.cookies = ",r.cookies)
    print("r.headers = ",r.headers)
    #print("r.text = ",r.text)
    print("r = ",r,type(r))
    data = r.json()

    jam_tracks = data['data']['tracks']
    random_choice = random.randint(0,len(jam_tracks))
    track = jam_tracks[random_choice]
    print("jam_track =",track)
    track_mp3 = track['mp3']
    track_date = track['show_date']
    track_set = track['set_name'].lower()
    track_venue = get_venue(track['show_id'])
    track_pretext = "Random Jamchart version of "+PHISHIN_SONG+" from "+track_venue
    if 'notes' in track:
        track_notes = track['notes']
    else:
        track_notes = "Check out this killer "+track_set+" "+PHISHIN_SONG+"!!"

    return jsonify(
        response_type='in_channel',
        text=track_pretext,
        attachments=[{'pretext':track_notes,'image_url':PHISHIN_LOGO,'title':track_date,'title_link':track_mp3}]
    )