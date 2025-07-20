import cv2
import matplotlib.pyplot as plt
import os

# Load image
image_file = "pg1.png"
img = cv2.imread(image_file)

if img is None:
    raise FileNotFoundError(f"Image '{image_file}' not found.")

# Convert original to RGB
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Invert image
inverted = cv2.bitwise_not(img)
inverted_rgb = cv2.cvtColor(inverted, cv2.COLOR_BGR2RGB)

# Save inverted image
os.makedirs("PROJWCT", exist_ok=True)
inverted_path = "PROJWCT/inverted.png"
cv2.imwrite(inverted_path, inverted)

# Display both using Matplotlib
plt.figure(figsize=(10, 5))

plt.subplot(1, 2, 1)
plt.imshow(img_rgb)
plt.title("Original")
plt.axis("off")

plt.subplot(1, 2, 2)
plt.imshow(inverted_rgb)
plt.title("Inverted")
plt.axis("off")

plt.tight_layout()
plt.show()

