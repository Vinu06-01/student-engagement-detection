const video = document.getElementById("camera");
const canvas = document.getElementById("snapshot");
const message = document.getElementById("cameraMessage");
const statusText = document.getElementById("statusText");
const confidenceText = document.getElementById("confidenceText");
const scoreText = document.getElementById("scoreText");
const outcomeText = document.getElementById("outcomeText");
const updatedText = document.getElementById("updatedText");

let predictionRunning = false;

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: 640,
                height: 480,
                facingMode: "user"
            },
            audio: false
        });

        video.srcObject = stream;

        message.textContent =
            "Camera active. Detection runs automatically every 3 seconds.";

        setInterval(sendFrame, 3000);
        setInterval(refreshStatus, 3000);

    } catch (error) {
        console.error("Camera Error:", error);

        message.textContent =
            "Camera permission is required for live engagement detection.";
    }
}

async function sendFrame() {

    if (predictionRunning) return;
    if (!video.videoWidth) return;

    predictionRunning = true;

    try {

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext("2d");

        context.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height
        );

        const image = canvas.toDataURL("image/jpeg", 0.6);

        const response = await fetch("/api/predict", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                image: image
            })
        });

        if (!response.ok) {
            console.error("Prediction request failed");
            return;
        }

        const result = await response.json();

        statusText.textContent = result.status;

        confidenceText.textContent =
            `Confidence: ${Number(result.confidence).toFixed(1)}%`;

    } catch (error) {

        console.error("Prediction Error:", error);

    } finally {

        predictionRunning = false;

    }
}

async function refreshStatus() {
    try {

        const response = await fetch("/api/student-status");

        if (!response.ok) return;

        const data = await response.json();

        statusText.textContent = data.current_status;

        confidenceText.textContent =
            `Confidence: ${Number(data.confidence).toFixed(1)}%`;

        scoreText.textContent =
            `${Number(data.attention_score).toFixed(1)}%`;

        outcomeText.textContent = data.final_outcome;
        updatedText.textContent = data.last_updated;

    } catch (error) {

        console.error("Status Refresh Error:", error);

    }
}

startCamera();