from PIL import Image
import os
import glob

MAX_HEIGHT = 1000

for side in ["left_image", "right_image"]:
    # Find the file, it could be png or jpg
    files = glob.glob(f"asset/{side}.*")
    if not files:
        print(f"Could not find {side} in asset/")
        continue
    
    # Exclude webp if it already exists
    file = [f for f in files if not f.endswith('.webp')][0]
    
    try:
        with Image.open(file) as img:
            # calculate new width
            ratio = MAX_HEIGHT / float(img.size[1])
            new_width = int((float(img.size[0]) * float(ratio)))
            
            img_resized = img.resize((new_width, MAX_HEIGHT), Image.Resampling.LANCZOS)
            
            # Save as webp
            new_file = f"asset/{side}.webp"
            img_resized.save(new_file, "WEBP", quality=85)
            print(f"Saved {new_file} with size {new_width}x{MAX_HEIGHT}")
    except Exception as e:
        print(f"Error processing {file}: {e}")
