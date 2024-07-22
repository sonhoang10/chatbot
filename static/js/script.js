async function submit_data() {
    var question = document.getElementById("questioninput").value;
    //loading animation
    var chat_container = document.querySelector(".chat_container");
    var spinner = document.createElement("div");
    spinner.classList.add("loading-spinner");

    onAppendClientChat();
    chat_container.appendChild(spinner);
    console.log("Question:", question);
    var response = await fetch("/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question: question }),
    });
  
    let accumulatedResponse = '';
    let audioFileName = null;
  
    if (response.body) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      spinner.remove();
  
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          console.log("Raw chunk from server:", chunk);
  
          const lines = chunk.split("\n\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const jsonChunk = line.slice(6);
              try {
                const parsedData = JSON.parse(jsonChunk);
                console.log("Response from server:", parsedData);
                onAppendBotChat(parsedData.content);
                accumulatedResponse += parsedData.content;
                audioFileName = parsedData.audio_filename;
                scrollToBottom();
              } catch (e) {
                console.error("Failed to parse JSON:", e, "Chunk:", jsonChunk);
              }
            }
          }
        }
        done = readerDone;
      }
  
      if (accumulatedResponse) {
        addSpeakerButton(accumulatedResponse);
      }
    }
  }
  
  function onAppendClientChat() {
    var chat_container = document.querySelector(".chat_container");
    var elQuestion = document.getElementById("questioninput");
    var chatQuestion = document.createElement("p");
    chatQuestion.classList.add("chat-question");
    chatQuestion.innerText = elQuestion.value;
    chat_container.appendChild(chatQuestion);
    elQuestion.value = "";
  }
  
  function onAppendBotChat(content) {
    var chat_container = document.querySelector(".chat_container");
  
    var lastChatResponse = chat_container.querySelector(".chat-response:last-child");
  
    if (lastChatResponse) {
      lastChatResponse.querySelector("span").innerText += content;
    } else {
      var chatResponse = document.createElement("p");
      chatResponse.classList.add("chat-response");
  
      var chatResponse_text = document.createElement("span");
      chatResponse_text.innerText = content || "";
      chatResponse.appendChild(chatResponse_text);
      chat_container.appendChild(chatResponse);
    }
  }
  
  function addSpeakerButton(answer) {
    var chat_container = document.querySelector(".chat_container");

    var response_icon = document.createElement("i");
    response_icon.classList.add("fa", "fa-volume-up");
    response_icon.setAttribute("aria-hidden", "true");

    var speaker = document.createElement("div");
    speaker.classList.add("speaker");
    speaker.appendChild(response_icon);
    chat_container.appendChild(speaker);

    response_icon.addEventListener("click", function () {
        loadAndPlayAudio(answer, speaker);
    });
}

  async function loadAndPlayAudio(answer, speakerElement) {
      let audioElement = speakerElement.querySelector("audio");
      
      if (!audioElement) {
        var spinner = document.createElement("div");
        spinner.classList.add("loading-spinner");
        spinner.style.marginLeft = "1rem";
        spinner.style.verticalAlign = "middle";
        spinner.style.display = "inline-block";
        speakerElement.appendChild(spinner);
          const response = await fetch('/tts', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify({ answer: answer }),
          });

          const data = await response.json();
          const audioId = data.audioId;
          spinner.remove();

          if (audioId) {
              audioElement = document.createElement("audio");
              audioElement.controls = "controls";
              audioElement.classList.add("chatResponse_audio");

              var audio_source = document.createElement("source");
              audio_source.src = "/mp3/" + audioId;
              audioElement.appendChild(audio_source);

              speakerElement.insertBefore(audioElement, speakerElement.firstChild);
          }
      }

      if (audioElement) {
          audioElement.play();
      }
  }
  
  function scrollToBottom() {
    var chat_container = document.querySelector(".chat_container");
    chat_container.scrollTop = chat_container.scrollHeight;
  }
  
  document.getElementById("questioninput").addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      document.getElementById("onClickAddChat").click();
    }
  });

function pageRotate(){
  let currentAngle = 120; // Initialize the current angle
  let targetAngle = 0; // Initialize the target angle to be the same as the current angle
  const maxChangeRate = 2; // Maximum change in degrees per update
  const updateInterval = 25; // Update interval in milliseconds
  let prevX = window.innerWidth / 2; // Initialize previous X to center of the screen
  let prevY = window.innerHeight / 2; // Initialize previous Y to center of the screen
  const delayFactor = 0.1; // Delay factor for smoothing (higher values increase delay)
  const stillTimeout = 500; // Timeout in milliseconds to consider the mouse still

  // Calculate the angle based on the change in mouse position
  function angleFromMovement(prevX, prevY, currX, currY) {
      const dx = currX - prevX;
      const dy = currY - prevY;
      let theta = Math.atan2(dy, dx); // range (-PI, PI]
      theta *= 180 / Math.PI; // rads to degs, range (-180, 180]
      return theta;
  }

  // Update targetAngle based on mouse movement
  let timeoutId = null;
  document.addEventListener("mousemove", (e) => {
      clearTimeout(timeoutId); // Clear previous timeout
      timeoutId = setTimeout(() => {
          targetAngle = currentAngle; // Reset targetAngle to currentAngle when still
      }, stillTimeout);

      setTimeout(() => {
          const currX = e.clientX;
          const currY = e.clientY;
          targetAngle += angleFromMovement(prevX, prevY, currX, currY);
          prevX = currX;
          prevY = currY;
      }, delayFactor * updateInterval);
  });

  function updateAngle() {
      // Calculate the difference between the current angle and the target angle
      let angleDiff = targetAngle - currentAngle;

      // Normalize the angle difference to be within the range [-180, 180]
      if (angleDiff > 180) {
          angleDiff -= 360;
      } else if (angleDiff < -180) {
          angleDiff += 360;
      }

      // Limit the change in angle to the maxChangeRate
      if (Math.abs(angleDiff) > maxChangeRate) {
          currentAngle += maxChangeRate * Math.sign(angleDiff);
      } else {
          currentAngle = targetAngle;
      }

      // Normalize the current angle to be within the range [0, 360]
      if (currentAngle >= 360) {
          currentAngle -= 360;
      } else if (currentAngle < 0) {
          currentAngle += 360;
      }

      // Set the document background to the current angle
      document.body.style.background = `linear-gradient(${currentAngle}deg, rgba(96, 227, 97, 1) 0%, rgb(0 125 44) 150%)`;
  }

  // Continuously update the background angle
  setInterval(updateAngle, updateInterval);

}
