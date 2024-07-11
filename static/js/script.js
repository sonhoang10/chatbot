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
        addAudioClip(accumulatedResponse);
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
  
  async function addAudioClip(answer) {
    const response = await fetch('/tts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ answer: answer }),
    });
  
    const data = await response.json();
    const audioId = data.audioId;
  
    if (audioId) {
      var chat_container = document.querySelector(".chat_container");
  
      var chatResponse_audio = document.createElement("audio");
      chatResponse_audio.controls = "controls";
      chatResponse_audio.classList.add("chatResponse_audio");
  
      var audio_source = document.createElement("source");
      audio_source.src = "/mp3/" + audioId;
      chatResponse_audio.appendChild(audio_source);
  
      var response_icon = document.createElement("i");
      response_icon.classList.add("fa", "fa-volume-up");
      response_icon.setAttribute("aria-hidden", "true");
  
      var speaker = document.createElement("div");
      speaker.classList.add("speaker");
      speaker.appendChild(chatResponse_audio);
      speaker.appendChild(response_icon);
      chat_container.appendChild(speaker);
  
      response_icon.addEventListener("click", function () {
        chatResponse_audio.play();
      });
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
  