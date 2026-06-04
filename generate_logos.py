import os
from PIL import Image, ImageDraw, ImageFont
from constants import TEAM_THEME, TEAM_LOGOS

def generate_placeholder_logos():
    base_dir = os.path.join(os.path.dirname(__file__), "static", "images", "teams")
    os.makedirs(base_dir, exist_ok=True)
    
    for team, data in TEAM_THEME.items():
        # Get path from TEAM_LOGOS
        rel_path = TEAM_LOGOS[team]
        full_path = os.path.join(os.path.dirname(__file__), "static", rel_path)
        
        # Create a 500x500 image
        img = Image.new('RGB', (500, 500), color=data["primary"])
        d = ImageDraw.Draw(img)
        
        # Try to use a nice font, fallback to default
        try:
            # Arial or similar standard font
            font = ImageFont.truetype("arialbd.ttf", 150)
        except:
            font = ImageFont.load_default()
            
        # Draw text in the center
        text = data["short"]
        
        # get text bounding box
        left, top, right, bottom = d.textbbox((0, 0), text, font=font)
        w = right - left
        h = bottom - top
        
        x = (500 - w) / 2
        y = (500 - h) / 2
        
        # Add a subtle circle background
        d.ellipse([20, 20, 480, 480], outline=data["text"], width=10)
        
        d.text((x, y), text, fill=data["text"], font=font)
        
        img.save(full_path)
        print(f"Generated {full_path}")

if __name__ == "__main__":
    generate_placeholder_logos()
