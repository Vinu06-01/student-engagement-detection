from collections import Counter, defaultdict, deque
import argparse
import json
import time
from pathlib import Path

import cv2
import mss
import numpy as np
import requests
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.models import load_model

parser = argparse.ArgumentParser(description="Real-time student engagement detection")
parser.add_argument(
    "--source",
    choices=["webcam", "screen"],
    default="webcam",
    help="Use webcam to show your face, or screen for Google Meet/Zoom grid detection.",
)
parser.add_argument("--camera", type=int, default=0, help="Webcam index. Usually 0.")
args = parser.parse_args()
ACTIVE_STUDENT_URL = "http://127.0.0.1:5000/active-student"

print(f"Starting {args.source}-based engagement detection...")

model = load_model("models/engagement_model.h5", compile=False)
print("Model loaded.")

class_file = Path("models/class_names.json")
if class_file.exists():
    classes = json.loads(class_file.read_text())
else:
    classes = ["disengaged", "engaged", "neutral"]
colors = {
    "engaged": (0, 180, 80),
    "neutral": (0, 215, 255),
    "disengaged": (0, 0, 255),
}
prediction_history = defaultdict(lambda: deque(maxlen=5))
confidence_history = defaultdict(lambda: deque(maxlen=8))

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# Adjust this area to match the Google Meet or Zoom window on your screen.
monitor = {
    "top": 100,
    "left": 100,
    "width": 1200,
    "height": 800,
}

if args.source == "screen":
    sct = mss.mss()
    print("Screen capture started. Press ESC to stop.")
else:
    print("Waiting for a student login before opening the webcam...")


def stable_label(student_id, label):
    prediction_history[student_id].append(label)
    return Counter(prediction_history[student_id]).most_common(1)[0][0]


def stable_confidence(student_id, confidence):
    confidence_history[student_id].append(float(confidence))
    return sum(confidence_history[student_id]) / len(confidence_history[student_id])


def filtered_faces(faces, frame_shape, webcam_mode=False):
    frame_h, frame_w = frame_shape[:2]
    frame_area = frame_h * frame_w
    good_faces = []

    for x, y, w, h in faces:
        area_ratio = (w * h) / frame_area
        aspect_ratio = w / max(h, 1)

        if w < 90 or h < 90:
            continue
        if area_ratio < 0.018:
            continue
        if not 0.68 <= aspect_ratio <= 1.35:
            continue

        good_faces.append((x, y, w, h))

    good_faces = sorted(good_faces, key=lambda face: face[2] * face[3], reverse=True)

    if webcam_mode and good_faces:
        return [good_faces[0]]
    return good_faces


def crop_face_with_margin(frame, x, y, w, h, margin=0.18):
    frame_h, frame_w = frame.shape[:2]
    pad_x = int(w * margin)
    pad_y = int(h * margin)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(frame_w, x + w + pad_x)
    y2 = min(frame_h, y + h + pad_y)
    return frame[y1:y2, x1:x2]


def get_active_student():
    try:
        response = requests.get(ACTIVE_STUDENT_URL, timeout=1)
        response.raise_for_status()
        payload = response.json()
        if payload.get("active"):
            return payload.get("student")
    except requests.RequestException:
        pass
    return None


def wait_for_active_student():
    while True:
        student = get_active_student()
        if student:
            return student
        print("No student logged in. Webcam is waiting...")
        time.sleep(2)


def send_update(student_id, status, confidence=0, face_detected=True, name=None):
    try:
        requests.post(
            "http://127.0.0.1:5000/update",
            json={
                "id": student_id,
                "name": name or student_id,
                "status": status,
                "confidence": round(float(confidence), 1),
                "face_detected": face_detected,
            },
            timeout=1,
        )
    except requests.RequestException:
        pass


def run_detection(active_student=None):
    if args.source == "webcam":
        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            raise RuntimeError("Camera not working. Try --camera 1 or check camera permission.")

        window_title = "Webcam Engagement Detection"
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 800, 600)
        cv2.moveWindow(window_title, 10, 30)
        print(f"Webcam started for {active_student.get('name', active_student['roll_no'])}. Press ESC to stop.")
    else:
        cap = None
        window_title = "Screen Engagement Detection"

    frame_count = 0

    while True:
        frame_count += 1

        if args.source == "webcam" and frame_count % 20 == 0:
            latest_student = get_active_student()
            if not latest_student:
                print("Student logged out. Closing webcam and waiting again...")
                cap.release()
                cv2.destroyWindow(window_title)
                return True
            active_student = latest_student

        if args.source == "webcam":
            student_id = active_student["roll_no"]
            student_name = active_student.get("name", student_id)
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab webcam frame.")
                break
            frame = cv2.flip(frame, 1)
        else:
            student_name = None
            screenshot = sct.grab(monitor)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=6,
            minSize=(80, 80),
        )
        faces = filtered_faces(faces, frame.shape, args.source == "webcam")

        print("Faces detected:", len(faces))

        if len(faces) == 0:
            no_face_id = active_student["roll_no"] if args.source == "webcam" else "Student1"
            no_face_name = active_student.get("name", no_face_id) if args.source == "webcam" else "Student1"
            send_update(no_face_id, "disengaged", 0, False, no_face_name)

            cv2.putText(
                frame,
                "No Faces Detected",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

        for i, (x, y, w, h) in enumerate(faces):
            if args.source == "webcam":
                student_id = active_student["roll_no"]
                student_name = active_student.get("name", student_id)
            else:
                student_id = f"Student{i + 1}"
                student_name = student_id
            face = crop_face_with_margin(frame, x, y, w, h)

            img = cv2.resize(face, (224, 224))
            img = preprocess_input(img.astype(np.float32))
            img = np.expand_dims(img, axis=0)

            prediction = model.predict(img, verbose=0)
            raw_label = classes[np.argmax(prediction)]
            label = stable_label(student_id, raw_label)
            confidence = stable_confidence(student_id, np.max(prediction) * 100)

            send_update(student_id, label, confidence, True, student_name)

            color = colors.get(label, (255, 255, 255))
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame,
                f"{student_name}: {label.title()} ({confidence:.1f}%)",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        cv2.imshow(window_title, frame)

        if cv2.waitKey(1) == 27:
            if args.source == "webcam":
                cap.release()
            cv2.destroyAllWindows()
            return False

    if args.source == "webcam":
        cap.release()
    cv2.destroyAllWindows()
    return False


if args.source == "webcam":
    while True:
        student = wait_for_active_student()
        should_wait_again = run_detection(student)
        if not should_wait_again:
            break
else:
    run_detection()
