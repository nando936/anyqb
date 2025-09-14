#!/usr/bin/env python
"""
Combine the 3 latest car document scans into a single PDF
"""
import os
from PIL import Image
from datetime import datetime

# Input files from VMware shared folder
input_files = [
    r"\\vmware-host\Shared Folders\Scanned Documents\Image.png",
    r"\\vmware-host\Shared Folders\Scanned Documents\Image (2).png",
    r"\\vmware-host\Shared Folders\Scanned Documents\Image (3).png"
]

# Output folder and file
output_folder = r"C:\Users\nando\Projects\anyqb\upload\cars"
output_filename = f"car_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
output_path = os.path.join(output_folder, output_filename)

# Create cars folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

print("Combining car documents...")
print(f"Reading files:")

# Load all images
images = []
for i, file_path in enumerate(input_files, 1):
    print(f"  {i}. {os.path.basename(file_path)}")
    img = Image.open(file_path)
    # Convert to RGB if necessary (PNG might have RGBA)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    images.append(img)

# Save as a single PDF
if images:
    print(f"\nSaving combined PDF to: {output_path}")
    images[0].save(output_path, save_all=True, append_images=images[1:])
    
    # Get file size
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # Convert to MB
    print(f"[OK] Combined PDF created successfully!")
    print(f"     File: {output_filename}")
    print(f"     Size: {file_size:.2f} MB")
    print(f"     Pages: {len(images)}")
else:
    print("[ERROR] No images found to combine")