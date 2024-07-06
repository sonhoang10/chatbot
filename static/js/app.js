var button = document.getElementById("microphone");
var input = document.getElementById("questioninput");
const playback = document.querySelector('.playback');

let active = false; //if button is clicked or not
let can_record =false;

let recorder = null;
let chunks = [];

window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const recognition = new SpeechRecognition();
recognition.interimResults = true;
recognition.lang = "vi-VN";
//recognition.start();




function SetupAudio(){
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia){
        navigator.mediaDevices
            .getUserMedia({
                audio: true
            })
            .then(SetupStream)
            .catch(err => {
                console.error(err)
            });
    }
}


function SetupStream(stream){
    recorder = new MediaRecorder(stream, {mineType: 'audio/wav'});
    recorder.mimeType = 'audio/wav';
    recorder.ondataavailable = e => {
        chunks.push(e.data);
    }

    recorder.onstop = e => {
        debugger
        const audioBlob = new Blob(chunks, { type: "audio/wav" })
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

       // var data = new FormData()
       // data.append('file', audioUrl , 'text.txt')

        // fetch('http://127.0.0.1:5000/audio', {
        //     method: 'POST',
        //     body: {
        //         data: {
        //             audio_url: audioUrl
        //         }
        //     }
  
        // })
        // let setting = 
        // $.ajax({url: "http://127.0.0.1:5000/audio", })

        var settings = {
            type: "POST",
            processData: true,
            data: {
                audio_url: audioUrl,
            },
            contenttype: "application/json",
        }
        $.ajax('http://127.0.0.1:5000/audio', settings).then(function(response) {

        });
        stream.getTracks()
            .forEach( track => track.stop() );
    }

}

recognition.addEventListener('result', e => {
    console.log(e.results)
    const transcript = Array.from(e.results)
        .map(result => result[0])
        .map(result => result.transcript)
        .join('')

        input.value = transcript;

    });

recognition.addEventListener('end', () => {
    button.style.backgroundColor = '#cccccc'
    active = false
 });

 recognition.addEventListener('start', () => {
    button.style.backgroundColor = 'red'
    active = true
 });

button.addEventListener ('click', () => {
    active = !active;


    if (active){
        button.style.backgroundColor = 'green'
        recognition.start();
    }
    else{
        button.style.backgroundColor = 'blue'
        recognition.stop;
    }
});


//SetupAudio();