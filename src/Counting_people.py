import serial
import time
import string
import pynmea2
import cv2
import numpy as np
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import threading

# ---------------- GOOGLE DRIVE SETUP ---------------- #
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = '/home/saket/Downloads/imagesraspi-14a192281ee9.json'
UPLOAD_FOLDER_ID = '1QeHWVbsJh2KKK57rJbDqzpi4xxsXjJRC'

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

def upload_to_drive(filepath, extra_data=""):
    file_metadata = {'name': os.path.basename(filepath), 'parents': [UPLOAD_FOLDER_ID]}
    media = MediaFileUpload(filepath, mimetype='image/jpeg' if filepath.endswith('.jpg') else 'text/plain')
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Uploaded {filepath} to Drive with File ID: {file.get('id')}")
        if extra_data:
            data_filename = f"{os.path.splitext(filepath)[0]}_data.txt"
            with open(data_filename, "w") as data_file:
                data_file.write(extra_data)
            upload_to_drive(data_filename)
            os.remove(data_filename)
    except Exception as e:
        print(f"Error uploading {filepath} to Drive: {e}")

# ---------------- GPS SETUP ---------------- #
port = "/dev/ttyAMA0"
ser = serial.Serial(port, baudrate=9600, timeout=0.5)

def get_gps_data(timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            line = ser.readline().decode("utf-8", errors='ignore').strip()
            if line.startswith('$GPRMC'):
                print("Raw GPS:", line)  # Debug: Optional
                msg = pynmea2.parse(line)
                if msg.status == 'A':  # 'A' = Active
                    lat = msg.latitude
                    lng = msg.longitude
                    return f"Latitude={lat} and Longitude={lng}"
        except pynmea2.ParseError:
            continue
        except Exception as e:
            print("GPS Read Error:", e)
    return "Latitude=Unknown and Longitude=Unknown"

# ---------------- OBJECT DETECTION SETUP ---------------- #
cv2.setUseOptimized(True)
cv2.setNumThreads(4)

classNames = []
classFile = "/home/saket/Desktop/Object_Detection_Files/coco.names"
with open(classFile, "rt") as f:
    classNames = f.read().rstrip("\n").split("\n")

configPath = "/home/saket/Desktop/Object_Detection_Files/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt"
weightsPath = "/home/saket/Desktop/Object_Detection_Files/frozen_inference_graph.pb"

net = cv2.dnn_DetectionModel(weightsPath, configPath)
net.setInputSize(256, 256)
net.setInputScale(1.0 / 127.5)
net.setInputMean((127.5, 127.5, 127.5))
net.setInputSwapRB(True)

def getObjects(img, thres, nms, draw=True, objects=[]):
    classIds, confs, bbox = net.detect(img, confThreshold=thres, nmsThreshold=nms)
    if len(objects) == 0:
        objects = classNames

    objectInfo = []
    if len(classIds) != 0:
        for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
            className = classNames[classId - 1]
            if className in objects:
                objectInfo.append([box, className])
                if draw:
                    cv2.rectangle(img, box, color=(0, 255, 0), thickness=2)
                    cv2.putText(img, className.upper(), (box[0], box[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    cv2.putText(img, f"{round(confidence * 100, 2)}%", (box[0], box[1] + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return img, objectInfo

def capture_frames(cap):
    global frame
    while True:
        success, frame = cap.read()
        if not success:
            break

# ---------------- MAIN LOGIC ---------------- #
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    cap.set(3, 320)
    cap.set(4, 240)

    frame_count = 0
    required_objects = ["person"]
    human_detected = False
    snapshot_count = 0
    last_snapshot_time = time.time()

    frame = None
    capture_thread = threading.Thread(target=capture_frames, args=(cap,))
    capture_thread.daemon = True
    capture_thread.start()

    while True:
        if frame is None:
            continue

        frame_count += 1
        if frame_count % 5 != 0:
            continue

        result, objectInfo = getObjects(frame, 0.4, 0.3, draw=True, objects=required_objects)

        person_count = 0  # Initialize person count for each frame
        for box, className in objectInfo:
            if className == "person":
                person_count += 1

        if person_count > 0 and time.time() - last_snapshot_time >= 10:
            human_detected = True
            snapshot_count += 1
            timestamp = time.strftime('%Y%m%d%H%M%S')
            image_filename = f"snapshot_{timestamp}.jpg"

            # Save snapshot
            cv2.imwrite(image_filename, frame)
            print(f"Snapshot saved as {image_filename}")

            # Get GPS data
            gps_data = get_gps_data()
            extra_data = f"{gps_data}, Human Count: {person_count}"
            print(f"Extra data: {extra_data}")

            # Upload both image and extra data to Drive
            upload_to_drive(image_filename, extra_data)

            last_snapshot_time = time.time()
        else:
            human_detected = False

        cv2.imshow("Output", result)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()