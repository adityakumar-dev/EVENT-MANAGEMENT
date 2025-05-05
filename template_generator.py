from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import os
import qrcode

def resize_image(image, box_size):
    """Resize and crop image to exactly fit the given box size, maintaining aspect ratio."""
    img_width, img_height = image.size
    box_width, box_height = box_size
    img_ratio = img_width / img_height
    box_ratio = box_width / box_height
    
    if img_ratio > box_ratio:
        new_height = box_height
        new_width = int(new_height * img_ratio)
    else:
        new_width = box_width
        new_height = int(new_width / img_ratio)
    
    image = image.resize((new_width, new_height), Image.LANCZOS)
    left = (new_width - box_width) // 2
    top = (new_height - box_height) // 2
    right = left + box_width
    bottom = top + box_height
    
    return image.crop((left, top, right, bottom))

def create_visitor_card(user_data):
    """
    Generate a visitor card for a user
    user_data should contain: name, profile_image_path, qr_code_path, user_id, institution_name
    """
    try:
        card_size = (1414, 2000)  # Portrait-oriented card
        template = Image.open("template/template2.png").resize(card_size)
        
        # Load user profile image
        try:
            profile_img = Image.open(user_data["profile_image_path"])
        except:
            # Fallback to placeholder if profile image loading fails
            profile_img = Image.new('RGB', (300, 300), 'gray')
        profile_img = resize_image(profile_img, (300, 300))
        
        # Load and process QR code
        try:
            qr_img = Image.open(user_data["qr_code_path"]).convert("RGBA")
            
            # Create a mask for the QR code
            data = qr_img.getdata()
            new_data = []
            for item in data:
                # If pixel is white or near-white, make it transparent
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))  # Transparent
                else:
                    new_data.append((0, 0, 0, 255))  # Solid black
            
            qr_img.putdata(new_data)
            qr_img = resize_image(qr_img, (650, 650))
            
        except Exception as e:
            print(f"Error processing QR code: {str(e)}")
            raise
        
        # Create a copy of template and convert to RGBA
        card = template.copy().convert("RGBA")
        
        # Layout positions
        profile_pos = (320, 910)  # Left side
        text_x = 650  # Right side for text fields
        qr_pos = ((card_size[0] - 650) // 2, 1350)  # Centered horizontally
        
        name_pos = (text_x, 970)
        id_pos = (text_x, 1040)
        institution_pos = (text_x, 1110)
        
        # Paste images
        card.paste(profile_img, profile_pos)
        card.paste(qr_img, qr_pos, qr_img)  # Use QR image as its own mask
        
        # Add text
        draw = ImageDraw.Draw(card)
        font_large = ImageFont.truetype("fonts/arial.ttf", 55)
        font_medium = ImageFont.truetype("fonts/arial.ttf", 40)
        
        draw.text(name_pos, f"Name: {user_data['name']}", fill="black", font=font_large, anchor="lm")
        draw.text(id_pos, f"ID: {user_data['user_id']}", fill="black", font=font_medium, anchor="lm")
        draw.text(institution_pos, f"Email: {user_data['email']}", fill="black", font=font_medium, anchor="lm")
        
        # Save the card
        os.makedirs("generated_cards", exist_ok=True)
        output_path = f"generated_cards/{user_data['name'].replace(' ', '_')}_visitor_card_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
        card.save(output_path, "PNG", quality=95)
        
        return output_path
        
    except Exception as e:
        print(f"Error generating visitor card: {str(e)}")
        raise

def generate_qr_code(data, output_path):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    qr_img.save(output_path)

# Test function
def main():
    os.makedirs("template", exist_ok=True)
    os.makedirs("fonts", exist_ok=True)
    os.makedirs("generated_cards", exist_ok=True)
    
    user = {
        "name": "John Doe",
        "user_id": "12345",
        "institution_name": "XYZ University"
    }
    
    profile_img_path = "template/john_doe_profile.jpg"
    qr_code_path = "template/john_doe_qrcode.png"
    
    generate_qr_code(f"https://example.com/{user['user_id']}", qr_code_path)
    
    user_data = {
        "name": user["name"],
        "profile_image_path": profile_img_path,
        "qr_code_path": qr_code_path,
        "user_id": user["user_id"],
        "institution_name": user["institution_name"]
    }
    
    output = create_visitor_card(user_data)
    print(f"Visitor card generated for {user['name']}: {output}")

if __name__ == "__main__":
    main()
