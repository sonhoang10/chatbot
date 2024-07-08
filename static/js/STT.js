var button = document.getElementById("microphone");
var input = document.getElementById("questioninput");

let active = false; //if button is clicked or not
let can_record =false;

let recorder = null;
let chunks = [];

window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const recognition = new SpeechRecognition();
recognition.interimResults = true;
recognition.lang = "vi-VN"; // no clue if this is working or not ¯\_(ツ)_/¯



recognition.addEventListener('result', e => { //updates the input based off the responses
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

