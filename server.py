import os
import base64
import time
import re
import requests
import json
import asyncio
from colorama import Fore
import wget

#for gpt and whisper STT
from openai import OpenAi

#audio processing
from pydub import AudioSegment, effects
import soundfile as sf
from pedalboard import Pedalboard, Chorus, Reverb, PitchShift, Delay

#TTS obviously
from elevenlabs import set_api_key
from elevenlabs import generate, save, stream
from gtts import gTTS

#browser shit
import ssl
from flask import request, session, Flask, send_file
from flask_socketio import SocketIO, Namespace, disconnect
from flask_cors import CORS


##
# Danomation
# GitHub: https://github.com/danomation
# Patreon https://www.patreon.com/Wintermute310
##

##
# API KEYS
client = OpenAI(api_key = "")
elevenlabs_api_key = ""
set_api_key(elevenlabs_api_key)
##

###
# APP VARIABLES
#
tts_provider = "google" # acceptable options, google (free) or elevenlabs (yes)
recordings_dir = "path/to/your/recordings/dir/" # notice the slash after
ssl_cert = "/path/to/your/fullchain.pem"
ssl_key = "/path/to/your/privkey.pem"
##

#define flask app
app = Flask("gptvoicewebsite")
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

#ssl shit
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.check_hostname = False
ssl_context.load_cert_chain(ssl_cert, keyfile=ssl_key)

if not os.path.exists(filePath):
    os.makedirs(filePath)

#file for what to output during dubious whisper hallucinations
mp3url = 'https://github.com/anars/blank-audio/blob/master/750-milliseconds-of-silence.mp3'
path_to_output_file = recordings_dir + "silence.mp3"
wget.download(url, path_to_output_file)

@app.errorhandler(Exception)
def handle_exception(e):
    # this section is supposed to handle errors but I haven't seen one yet. I probably need to handle ssl errors in addition to this.
    if isinstance(e, HTTPException):
        return e
    return render_template("500_generic.html", e=e), 500

def sendgpt(message, session_history):
    messages = []
    messages = session_history
    chat = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=1.2,
        max_tokens=1024,
        user="web"
    )
    session_history.append({"role": "assistant","content": chat.choices[0].message.content},)
    reply =  str(chat.choices[0].message.content)
    return reply, session_history

def sendtts(message):
    time_stamp = str(time.time())
    file_path = recordings_dir + "reply_" + time_stamp + ".mp3"
    if tts_provider == "elevenlabs":
        voice="Rachel",
        #voice="vKECufy6OSQM8LSmvMEi", #my voice selection private to me - wintermute
        model="eleven_turbo_v2",
        stream=False
        )
        save(audio, file_path)
        return file_path
    else:
        #use free gTTS and add some style to it.
        tts = gTTS(message, tld="us") #'us') # tld='co.uk')
        tts.save(file_path)

        #add input from gTTS to pydub for processing and eventual input to spotify pedalboard
        sound = AudioSegment.from_mp3(file_path)
        file_path2 = recordings_dir + "reply_" + time_stamp + ".wav"
        sound = sound._spawn(sound.raw_data, overrides={
         "frame_rate": int(sound.frame_rate * 1.5)
        })
        sound.export(file_path2, format="wav")

        # Read in the wav to Pedalboard
        audio, sample_rate = sf.read(file_path2)
        # Add some style to it
        board = Pedalboard([Chorus(), Reverb(room_size=0.35), PitchShift(semitones=-11)])
        effected = board(audio, sample_rate)
        file_path3 = recordings_dir + "reply_" + time_stamp + ".wav"
        # Write the updated audio (wav file):
        sf.write(file_path3, effected, sample_rate)
        return file_path3

user_sessions = {}

class AudioNamespace(Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.user_sessions = {}

    def on_connect(self):
        session['sid'] = request.sid
        print('-- Session ' + str(session['sid']) + ' connected to /audio')
        #userSessions[session['sid']] = {'history': []}
        self.user_sessions[session['sid']] = {'history': [{"role": "system","content": "Act as a cyberpunk robot named Wintermute. Reply Limit is 35 words. Don't use urls, Hashtags, or emojis"},]}


    def on_disconnect(self):
        print('-- Session ' + str(session['sid']) + ' disconnected from /audio')
        print('A user disconnected from /audio')

    def on_audio(self, data):
        # Handle the audio data from the client here. Define their SID for sessions
        current_session = self.user_sessions[request.sid]

    def on_upload_audio(self, audioData):
        # Grab the audio from the session and decode the base64 data
        print('-- Received uploaded audio file for session ' + str(session['sid'])) #, audioData)
        audioBuffer = base64.b64decode(audioData.split(",")[1])

        # Path for the new audio file
        filePath = recordings_dir
        outputfile = f"{int(time.time())}_audio.ogg"
        filePath = os.path.join(filePath, outputfile)

        #Write the audio data to a new .ogg file
        with open(filePath, "wb") as audioFile:
            audioFile.write(audioBuffer)
            print('-- File saved for session ' + str(session['sid']))
        audio_file = open(recordings_dir + outputfile, "rb")
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)) 
        print(transcript)
        transcript = str(transcript.text)

        #regex to match only english characters - helps with whisper hallucinations. 
        #This conditional is just throwing out dubious recordings and then ultimately sending to GPT, then TTS, then back to user
        expression = r'[^\x00-\x7F]+'
        match =  re.search(expression, transcript)
        if match:
            filePathSend = recordings_dir + "silent.mp3" #grab it from https://github.com/anars/blank-audio/blob/master/750-milliseconds-of-silence.mp3
            with open(filePathSend, "rb") as audioToSend:
                audioDataSend = audioToSend.read()
                dataToSend = {'type': 'audio/mp3', 
                'data': audioDataSend  # This is the audio blob data to send
            }
            self.emit('audio', dataToSend, room=session['sid'])
        elif transcript == "Please click Subscribe and LIKE. It's a big help to me." or transcript == "If you have any questions, please leave a comment." or transcript == "Thank you for your time." or transcript == "If you find the video useful, please like, share the video, and subscribe. Thanks for watching it." or transcript == "If you have any questions, please post them in the comments." or transcript == "Please subscribe to my channel." or transcript == "Thank you for watching the video." or transcript == "If you have any questions or comments, please post them in the comments section." or transcript == "If you find the video useful, please like, share the video, and subscribe." or transcript == "" or transcript == "If you find the video useful, please like, share the video, and subscribe. Thanks for watching." or transcript == "If you have any questions or other problems, please post them in the comments." or transcript == "チャンネル登録をお願いいたします" or transcript == "먹방끝 빠이빠이" or transcript == "Bye for now." or transcript == "Thanks for watching!" or transcript == ". ." or transcript == "Дякую за перегляд!" or transcript == "to to to" or transcript == "Дякуємо за перегляд і до зустрічі у наступному відео!" or transcript == "Thank you for watching." or transcript == "Peace." or transcript == "MBC 뉴스 이덕영입니다." or transcript == "Oh" or transcript == "You" or transcript == "you" or transcript == "oh":
        #a metric fuckton of hallucinations
            filePathSend = recordings_dir + silent.mp3" #grab it from https://github.com/anars/blank-audio/blob/master/750-milliseconds-of-silence.mp3
            with open(filePathSend, "rb") as audioToSend:
                audioDataSend = audioToSend.read()
                dataToSend = {'type': 'audio/mp3', 
                    'data': audioDataSend  # This is the audio blob data to send
            }
            self.emit('audio', dataToSend, room=session['sid'])
        else:
            #output this user's transcript to console
            print(str(session['sid']) + Fore.YELLOW + " user: " + Fore.WHITE + transcript)
            f = open(recordings_dir + "chat.txt", "a")
            f.write(str(session['sid'][:4 ]) + "@switchmeme: " + transcript + "\n") #grab the session sid for the chat
            f.close()

            current_session = self.user_sessions[request.sid]
            current_session['history'].append({"role": "user","content": transcript},) # depending on what you want to add to history

            # Get the first history item
            first = [current_session['history'][0]]
            # Get the last 10 history items
            last_ten = current_session['history'][-10:]
            selected_history = first + last_ten

            # send conversation and last ten history to gpt and return the response with the updated history
            response, current_session['history'] = sendgpt(transcript, selected_history)

            #output wintermute's response to console
            print(str(session['sid']) + Fore.GREEN + " Wintermute: " + Fore.WHITE + response)

            f = open(recordings_dir + "chat.txt", "a")
            f.write("wintermute: " + response + "\n\n")
            f.close()

            response_audio_path = sendtts(response)

            filePathSend = response_audio_path
            with open(filePathSend, "rb") as audioToSend:
                audioDataSend = audioToSend.read()
                dataToSend = {'type': 'audio/wav',  # Update this to match the audio data type
                    'data': audioDataSend  # This is the audio blob data to send
                }
            self.emit('audio', dataToSend, room=session['sid'])

socketio.on_namespace(AudioNamespace('/audio'))
socketio.run(app, host='0.0.0.0', port=5000, ssl_context=ssl_context, allow_unsafe_werkzeug=True)
