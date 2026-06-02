import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

print("Training started...")

dataset_path = Path("dataset")
model_dir = Path("models")
model_dir.mkdir(exist_ok=True)

img_size = (224, 224)
batch_size = 8
seed = 123
class_names = ["disengaged", "engaged", "neutral"]

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def crop_largest_face(image_path):
    image = cv2.imread(str(image_path))
    if image is None:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=5,
        minSize=(70, 70),
    )

    if len(faces) == 0:
        crop = image
    else:
        x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
        pad_x = int(w * 0.18)
        pad_y = int(h * 0.18)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(image.shape[1], x + w + pad_x)
        y2 = min(image.shape[0], y + h + pad_y)
        crop = image[y1:y2, x1:x2]

    crop = cv2.resize(crop, img_size)
    crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    return crop


images = []
labels = []
for label_index, class_name in enumerate(class_names):
    class_dir = dataset_path / class_name
    for image_path in class_dir.glob("*"):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
            continue
        cropped = crop_largest_face(image_path)
        if cropped is not None:
            images.append(cropped)
            labels.append(label_index)

images = np.array(images, dtype=np.float32)
labels = np.array(labels, dtype=np.int32)

if len(images) < 12:
    raise RuntimeError("Not enough training images. Add more images to dataset folders.")

print("Classes:", class_names)
print("Total images:", len(images))
for index, name in enumerate(class_names):
    print(f"{name}: {(labels == index).sum()}")

rng = np.random.default_rng(seed)
indices = rng.permutation(len(images))
images = images[indices]
labels = labels[indices]

split_index = max(1, int(len(images) * 0.8))
train_images, val_images = images[:split_index], images[split_index:]
train_labels, val_labels = labels[:split_index], labels[split_index:]

train_data = tf.data.Dataset.from_tensor_slices((train_images, train_labels))
val_data = tf.data.Dataset.from_tensor_slices((val_images, val_labels))

data_aug = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.08),
    layers.RandomZoom(0.15),
    layers.RandomContrast(0.15),
    layers.RandomBrightness(0.12),
])


def prepare_train(x, y):
    x = data_aug(x)
    x = preprocess_input(tf.cast(x, tf.float32))
    return x, y


def prepare_val(x, y):
    x = preprocess_input(tf.cast(x, tf.float32))
    return x, y


AUTOTUNE = tf.data.AUTOTUNE
train_data = (
    train_data.shuffle(len(train_images), seed=seed)
    .batch(batch_size)
    .map(prepare_train)
    .prefetch(AUTOTUNE)
)
val_data = val_data.batch(batch_size).map(prepare_val).prefetch(AUTOTUNE)

class_counts = np.bincount(train_labels, minlength=len(class_names))
class_weights = {
    index: float(len(train_labels) / (len(class_names) * max(count, 1)))
    for index, count in enumerate(class_counts)
}
print("Class weights:", class_weights)

base_model = tf.keras.applications.MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet",
)
base_model.trainable = False

model = models.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.BatchNormalization(),
    layers.Dense(128, activation="relu"),
    layers.Dropout(0.45),
    layers.Dense(len(class_names), activation="softmax"),
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(0.0002),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy",
        patience=10,
        restore_best_weights=True,
    ),
    tf.keras.callbacks.ModelCheckpoint(
        str(model_dir / "best_model.h5"),
        monitor="val_accuracy",
        save_best_only=True,
    ),
]

history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=45,
    class_weight=class_weights,
    callbacks=callbacks,
)

base_model.trainable = True
for layer in base_model.layers[:-35]:
    layer.trainable = False

model.compile(
    optimizer=tf.keras.optimizers.Adam(0.00002),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

fine_history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=20,
    class_weight=class_weights,
    callbacks=callbacks,
)

model.save(model_dir / "engagement_model.h5")
(model_dir / "class_names.json").write_text(json.dumps(class_names, indent=2))
print("Model saved to models/engagement_model.h5")
print("Class names saved to models/class_names.json")

all_accuracy = history.history["accuracy"] + fine_history.history["accuracy"]
all_val_accuracy = history.history["val_accuracy"] + fine_history.history["val_accuracy"]

plt.figure(figsize=(8, 5))
plt.plot(all_accuracy, label="Train")
plt.plot(all_val_accuracy, label="Validation")
plt.xlabel("Epochs")
plt.ylabel("Accuracy")
plt.legend()
plt.title("Engagement Model Accuracy")
plt.tight_layout()
plt.savefig(model_dir / "training_accuracy.png")
print("Accuracy graph saved to models/training_accuracy.png")
