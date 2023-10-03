//
// **ATTRIBUTION TO Pomme** - I didn't make the frontend javascript file script.js!
// GitHUB https://github.com/Pxmme
// Twitter https://twitter.com/pxmme1337
//

let socket = io.connect('https://your website dot com:5000/audio'); // set to your website
let mediaRecorder;
let audioChunks = [];
let silenceStart = 0;
let recording = false;
const ONE_SECOND = 1000; // milliseconds
const ONE_SECOND_AND_HALF = 1500; // milliseconds
const TWO_SECONDS = 2000; // milliseconds
let playbackSource = null; // A global reference to the audio source
let currentAudioElement = null;
let stream;
let startTime = 0;
let audioContext;
let analyser;
let source;
let isPlaying = false;
let dataArray;

async function requestMicrophoneAccess() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        startListening();
    } catch (error) {
        console.error("Microphone access denied or error occurred:", error);
        // Gérez l'erreur comme vous le souhaitez ici.
    }
}



function stopPlayback() {
    if (playbackSource) {
        playbackSource.stop();
        playbackSource = null;
    }
}

async function startListening() {
    if (!stream) {
        console.error("Stream is not available.");
        return;
    }

    audioContext = new AudioContext();
    analyser = audioContext.createAnalyser();
    source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
        console.log(audioContext.state);
    function startMediaRecorder() {
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

                mediaRecorder.onstop = async () => {
                        const endTime = new Date().getTime();
                        const recordingDuration = endTime - startTime;

                        if (recordingDuration > ONE_SECOND_AND_HALF) {  // Vérifiez si la durée est supérieure à deux secondes
                                const audioBlob = new Blob(audioChunks, { type: 'audio/m4a' });
                                const reader = new FileReader();
                                reader.readAsDataURL(audioBlob);
                                reader.onloadend = () => {
                                        const base64data = reader.result;
                                        socket.emit('upload_audio', base64data);
                                };
                                console.log('File ready to be sent');
                        } else {
                                console.log('Audio is less than 1.5s, not sending');
                                startListening();
                                console.log('Started listening again.');
                        }
                        audioChunks = [];
                };
    }

    // Check audio levels for silence or noise
    analyser.fftSize = 512;
    const bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);

    function checkAudioLevels() {
        analyser.getByteFrequencyData(dataArray);
        const values = dataArray;
        const length = values.length;
        let sum = 0;

        for (let i = 0; i < length; i++) {
            sum += values[i];
        }

        const average = sum / length;

        if (average < 20 && recording) { // Detected silence
            if (silenceStart === 0) silenceStart = new Date().getTime();
            if (new Date().getTime() - silenceStart > ONE_SECOND) {
                mediaRecorder.stop();
                recording = false;
                return;
            }
        } else if (average >= 20 && !recording && !playbackSource) { // Detected noise
            startMediaRecorder();
            mediaRecorder.start();
            recording = true;
            silenceStart = 0;
                        startTime = new Date().getTime();
        } else if (average >= 20 && recording) { // Still noisy
            silenceStart = 0;
        } else if (average >= 20 && playbackSource) {
            stopPlayback(); // If there's noise while playing back, stop the playback
        }

        requestAnimationFrame(checkAudioLevels);
    }

    checkAudioLevels(); // Start the audio check loop immediately after initialization
}



function createVisualizer(source) {
    analyser = audioContext.createAnalyser();
    source.connect(analyser);

    dataArray = new Uint8Array(analyser.frequencyBinCount);

    // La fonction pour mettre à jour la visualisation


    updateVisualizer(); // Démarrer la visualisation
}

function updateVisualizer() {
        if (isPlaying) {
                analyser.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
          
                const circle = document.getElementById("circle");
                const scaleFactor = Math.max(0.2, Math.min(10, average / 128));
                circle.style.setProperty('--scale-factor', scaleFactor);
                circle.style.setProperty('filter', 'blur(0px) sepia(100%) saturate(200%) brightness(100%) hue-rotate(100deg) drop-shadow(12px 12px 25px rgba(0,100,100,0.8)');
                circle.style.setProperty('opacity', '0.7');
                requestAnimationFrame(() => updateVisualizer());
        }
}

socket.on('audio', function(data) {
    console.log("Received audio of type: ", data.type);

    if (currentAudioElement) {
        currentAudioElement.pause();
        URL.revokeObjectURL(currentAudioElement.src);  // Free up memory
    }

    const audioBlob = new Blob([data.data], { type: 'audio/mp3' });
    const audioURL = URL.createObjectURL(audioBlob);

    currentAudioElement = new Audio(audioURL);
    currentAudioElement.play();
        isPlaying = true;
    currentAudioElement.onended = () => {
        URL.revokeObjectURL(audioURL);
                startListening();
                const circle = document.getElementById("circle");
                circle.style.removeProperty('--scale-factor');
                circle.style.setProperty('animation', 'pulse 2s infinite alternate');
                circle.style.setProperty('opacity', '0.6');
                circle.style.setProperty('filter', 'blur(0.2px) sepia(100%) saturate(200%) brightness(70%) hue-rotate(330deg) drop-shadow(12px 12px 25px rgba(100,20,20,0.8)');
                isPlaying = false;
    };
        const audioSource = audioContext.createMediaElementSource(currentAudioElement);
    audioSource.connect(audioContext.destination); // Ajoutez cette ligne
    createVisualizer(audioSource);
});

window.onload = requestMicrophoneAccess;
