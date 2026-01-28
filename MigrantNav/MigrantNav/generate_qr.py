import qrcode
import sys

# Get URL from user input
url = input("🔗 Paste your ngrok URL here: ").strip()

# Create QR Code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

# Create an image from the QR Code
img = qr.make_image(fill_color="black", back_color="white")

# Save it
filename = "chatbot_access.png"
img.save(filename)

print(f"✅ QR Code saved as '{filename}'. Open it and scan with your phone!")