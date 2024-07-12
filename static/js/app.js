var button = document.getElementById("microphone");
const icon = button.querySelector('i');
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
    active = false
    icon.style.animation = 'none'
    icon.style.color = 'black'
    icon.style.fontSize = "16px"
 });

 recognition.addEventListener('start', () => { //changes the color of mic when starting
    icon.style.animation = 'pulseRed 2s infinite ease-in-out'
    //animation for the span of the button
    icon.style.columnSpan.animation = 'pulse 2 2s infinite ease-in-out'
    //set button active to true
    button.active = true


    active = true
 });




button.addEventListener ('click', () => { //decides whether or not to stop or start recording depending on active status
    active = !active;


    if (active){
        icon.style.animation = 'none'
        icon.style.color = 'green'
        recognition.start();
    }
    else{
        icon.style.animation = 'blink 1s infinite'
        recognition.stop;
    }
});


//SetupAudio();