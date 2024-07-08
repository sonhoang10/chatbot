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



recognition.addEventListener('result', e => { //updates the input
    console.log(e.results)
    const transcript = Array.from(e.results)
        .map(result => result[0])
        .map(result => result.transcript)
        .join('')

        input.value = transcript;

    });


recognition.addEventListener('end', () => { //changes the color of mic when ending
    button.style.backgroundColor = '#cccccc'
    active = false
 });

 recognition.addEventListener('start', () => { //changes the color of mic when starting
    button.style.backgroundColor = 'red'
    active = true
 });




button.addEventListener ('click', () => { //decides whether or not to stop or start recording depending on active status
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