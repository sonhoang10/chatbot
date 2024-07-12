const fileList = document.querySelector(".file-list");
const fileBrowseButton = document.querySelector(".file-browse-button");
const fileBrowseInput = document.querySelector(".file-browse-input");
const fileUploadBox = document.querySelector(".file-upload-box");
const fileCompletedStatus = document.querySelector(".file-completed-status");
const refreshButton = document.querySelector('.upload-button');
const downloadButton = document.querySelector('.download-button');
const resetButton = document.querySelector('.reset-button');
const testButton = document.querySelector('.test-button');
const backgroundToggle = document.querySelector('.switch')
const checkbox = document.getElementById('checkbox');
const bgBool = document.getElementById('BGActive')

let totalFiles = 0;
let completedFiles = 0;
// Function to create HTML for each file item
const createFileItemHTML = (file, uniqueIdentifier, uploading = true) => {
    const { name, size } = file;
    const extension = name.split(".").pop();
    const formattedFileSize = size >= 1024 * 1024 ? `${(size / (1024 * 1024)).toFixed(2)} MB` : `${(size / 1024).toFixed(2)} KB`;

    return `<li class="file-item ${uploading ? 'uploading' : 'completed'}" id="file-item-${uniqueIdentifier}">
                <div class="file-extension">${extension}</div>
                <div class="file-content-wrapper">
                    <div class="file-content">
                        <div class="file-details">
                            <h5 class="file-name">${name}</h5>
                            <div class="file-info">
                                <small class="file-size">${uploading ? `0 MB / ${formattedFileSize}` : formattedFileSize}</small>
                                <small class="file-divider">•</small>
                                <small class="file-status">${uploading ? 'Uploading...' : 'Completed'}</small>
                            </div>
                        </div>
                        <button class="cancel-button" data-filename="${name}">
                            <i class="bx bx-x"></i>
                        </button>
                    </div>
                    ${uploading ? '<div class="file-progress-bar"><div class="file-progress"></div></div>' : ''}
                </div>
            </li>`;
}
// Function to handle file uploading
const handleFileUploading = (file, uniqueIdentifier) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);
    
    xhr.upload.addEventListener("progress", (e) => {
        const fileProgress = document.querySelector(`#file-item-${uniqueIdentifier} .file-progress`);
        const fileSize = document.querySelector(`#file-item-${uniqueIdentifier} .file-size`);
        const formattedFileSize = file.size >= 1024 * 1024 ? `${(e.loaded / (1024 * 1024)).toFixed(2)} MB / ${(e.total / (1024 * 1024)).toFixed(2)} MB` : `${(e.loaded / 1024).toFixed(2)} KB / ${(e.total / 1024).toFixed(2)} KB`;
        const progress = Math.round((e.loaded / e.total) * 100);
        fileProgress.style.width = `${progress}%`;
        fileSize.innerText = formattedFileSize;
    });
    
    xhr.open("POST", "/files", true);
    xhr.send(formData);
    showPopup('File uploaded successfully', '#00B125');
    
    return xhr;
};

//function to fetch files on the server
const fetchExistingFiles = () => {
    fetch('/files/list')
        .then(response => response.json())
        .then(files => {
            files.forEach((file, index) => {
                const uniqueIdentifier = Date.now() + index;
                const fileItemHTML = createFileItemHTML(file, uniqueIdentifier, false);
                fileList.insertAdjacentHTML("afterbegin", fileItemHTML);
                const currentFileItem = document.querySelector(`#file-item-${uniqueIdentifier}`);
                const deleteButton = currentFileItem.querySelector(".cancel-button");
                
                if (deleteButton) {
                    deleteButton.addEventListener("click", () => {
                        currentFileItem.remove(); // Adjust as needed if accounting for completed files
                        updateFileCompletedStatus();
                    });
                }
                
                updateFileStatus(currentFileItem, "Completed", "#00B125");
            });
            completedFiles += files.length;
            totalFiles += files.length;
            updateFileCompletedStatus();
        })
        .catch(error => console.error('Error fetching existing files:', error));
};

//updates file status
const updateFileStatus = (fileItem, status, color) => {
    fileItem.querySelector(".file-status").innerText = status;
    fileItem.querySelector(".file-status").style.color = color;
};

// Function to handle selected files
const handleSelectedFiles = ([...files]) => {
    if(files.length === 0) return; // Check if no files are selected
    totalFiles += files.length;
    files.forEach((file, index) => {
        const uniqueIdentifier = Date.now() + index;
        const fileItemHTML = createFileItemHTML(file, uniqueIdentifier,true);
        fileList.insertAdjacentHTML("afterbegin", fileItemHTML);
        const currentFileItem = document.querySelector(`#file-item-${uniqueIdentifier}`);
        const cancelFileUploadButton = currentFileItem.querySelector(".cancel-button");
        const xhr = handleFileUploading(file, uniqueIdentifier);
        const updateFileStatus = (status, color) => {
            currentFileItem.querySelector(".file-status").innerText = status;
            currentFileItem.querySelector(".file-status").style.color = color;
        }
        xhr.addEventListener("readystatechange", () => {
            if(xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                completedFiles++;
                updateFileStatus("Completed", "#00B125");
                currentFileItem.classList.remove('uploading');
                currentFileItem.classList.add('completed');
                currentFileItem.querySelector(".file-size").innerText = currentFileItem.querySelector(".file-size").innerText.split("/")[1].trim();
                updateFileCompletedStatus();
            }
        });
        cancelFileUploadButton.addEventListener("click", () => {
            xhr.abort();
            currentFileItem.remove();
        });
    });
    updateFileCompletedStatus();
}

// Function to handle file deletion
const handleFileDeletion = (filename, fileItemElement) => {
    console.log('Deleting file:', filename); // Added for debugging
    fetch('/files/delete', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message === "File deleted successfully") {
            fileItemElement.remove();
            totalFiles--;
            updateFileCompletedStatus();
            showPopup('File deleted successfully');
        } else {
            alert(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        popupMessage('An error occurred while trying to delete the file', '#E3413F');
    });
};

//function to load all files into vectorDB
function loadFilesToChat(_callback) {
    fetch('/files/chatLoader', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
            // You can update the UI or perform any other operations here
            showPopup('Database loaded');
            //callback
            _callback();
        })
        .catch(error => {
            console.error('Error:', error);
            showPopup('An error occurred while trying to reload the database', '#E3413F');
            _callback();
        });
}

function resetChat(_callback) {
    fetch('/files/resetChat', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
            // You can update the UI or perform any other operations here
            showPopup('Chat Reset');
        })
        .catch(error => {
            console.error('Error:', error);
            showPopup('An error occurred while trying to reset chat', '#E3413F');
            _callback();
        });
    //callback
    _callback();
}

function showPopup(message, color = '#7e7e7e') {
    // Create the popup element
    const popup = document.createElement('div');
    popup.className = 'popup-message fade-in';
    popup.textContent = message;
    popup.style.backgroundColor = color;

    // Append the popup to the body
    document.body.appendChild(popup);

    // Automatically remove the popup using fade in and fade out after 3 seconds
    setTimeout(() => {
        popup.classList.remove('fade-in');
        popup.classList.add('fade-out');
        popup.addEventListener('animationend', () => {
            popup.remove();
        });
    }, 3000);
}
//downloads chat history
function downloadChatHistory(_callback) {
    fetch('/files/historyDownload', { method: 'POST' })
        .then(res => {
            if (!res.ok) {
                throw new Error('Network response was not ok');
            }
            return res.blob();
        })
        .then(blob => {
            download(blob);
        })
        .catch(err => {
            console.error('Error downloading file:', err);
            showPopup('Chat history does not exist', '#E3413F');
            // Handle the error, e.g., show an error message
        })
        .finally(() => {
            // Callback to execute after attempt to download
            _callback();
        });
}

function testFunction(_callback) {
     // Show loading spinner
    setTimeout(() => {
        showPopup('Test completed'); // Hide loading spinner after completion
        _callback(); // Call the callback function after completion
    }, 3000);
}

function backgroundTogg(_callback){
    fetch('/background', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log(data.bool);
            // You can update the UI or perform any other operations here
            var popupTxt = 'Animated background is ' + data.bool
            showPopup(popupTxt);
            if (data.bool == "True"){
                pageRotate();
            }
            else{
                stopPageRotate();
            }
            return data.bool;
        })
        .catch(error => {
            console.error('Error:', error);
            showPopup('An error occurred while toggling background animations', '#E3413F');
        });
}

// Function to handle file drop event
fileUploadBox.addEventListener("drop", (e) => {
    e.preventDefault();
    handleSelectedFiles(e.dataTransfer.files);
    fileUploadBox.classList.remove("active");
    fileUploadBox.querySelector(".file-instruction").innerText = "Drag files here or";
});
// Function to handle file dragover event
fileUploadBox.addEventListener("dragover", (e) => {
    e.preventDefault();
    fileUploadBox.classList.add("active");
    fileUploadBox.querySelector(".file-instruction").innerText = "Release to upload or";
});
// Function to handle file dragleave event
fileUploadBox.addEventListener("dragleave", (e) => {
    e.preventDefault();
    fileUploadBox.classList.remove("active");
    fileUploadBox.querySelector(".file-instruction").innerText = "Drag files here or";
});

const updateFileCompletedStatus = () => {
    fileCompletedStatus.innerText = `${completedFiles} / ${totalFiles} files completed`;
};

fileBrowseInput.addEventListener("change", (e) => handleSelectedFiles(e.target.files));
fileBrowseButton.addEventListener("click", () => fileBrowseInput.click());

// Function to handle clicks
document.addEventListener("DOMContentLoaded", () => {
    fetchExistingFiles();

    if(bgBool){
        if (bgBool.value == 'true'){
            checkbox.checked = true;
        }
    }

    fileList.addEventListener('click', (e) => {
        const cancelButton = e.target.closest('.cancel-button');
        if (cancelButton) {
            const fileItemElement = cancelButton.closest('.file-item');
            const filename = cancelButton.getAttribute('data-filename'); // Fetch the data-filename directly from the clicked element

            if (filename) {
                handleFileDeletion(filename, fileItemElement);
            } else {
                fileItemElement.remove(); // Adjust as needed
                updateFileCompletedStatus();
            }
        }
    });

    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            refreshButton.classList.add('loading');
            loadFilesToChat(function() {
                refreshButton.classList.remove('loading');
            });
        });
    }

    if (downloadButton) {
        downloadButton.addEventListener('click', () => {
            downloadButton.classList.add('loading');
            downloadChatHistory(function() {
                downloadButton.classList.remove('loading');
            });
        });
    }

    if (resetButton) {
        resetButton.addEventListener('click', () => {
            resetButton.classList.add('loading');
            resetChat(function() {
                resetButton.classList.remove('loading');
            });
        });
    }

    if (testButton) {
        testButton.addEventListener('click', () => {
            testButton.classList.add('loading');
            testFunction(function() {
                testButton.classList.remove('loading');
            });
        });
    }

    if (checkbox){
        checkbox.addEventListener('change', (event) => {
            console.log('Checkbox changed');
            backgroundTogg();
        
        });
    }
});

let rotateIntervalId = null; // Variable to store the interval ID

function pageRotate() {
    let currentAngle = 120; // Initialize the current angle
    let targetAngle = 0; // Initialize the target angle to be the same as the current angle
    const maxChangeRate = 5; // Maximum change in degrees per update
    const updateInterval = 75; // Update interval in milliseconds
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

    // Continuously update the background angle and store the interval ID
    rotateIntervalId = setInterval(updateAngle, updateInterval);

    // Return the interval ID so it can be stored outside this function
    return rotateIntervalId;
}

function stopPageRotate() {
    if (rotateIntervalId !== null) {
        clearInterval(rotateIntervalId);
        rotateIntervalId = null; // Reset the interval ID
    }
    document.body.style.background = '#04aa6d';
}