# ENHANCED MODELS with additional features (models.py - Enhanced)
from django.db import models
from django.contrib.auth.models import User
import uuid
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import math

class MessagePage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200, default="Love Messages")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    text_color = models.CharField(max_length=7, default="#FF69B4")
    background_color = models.CharField(max_length=7, default="#000000")
    animation_speed = models.FloatField(default=1.0)
    is_public = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    
    def get_absolute_url(self):
        return f"/view/{self.id}/"
    
    def generate_heart_qr(self, request):
        """Generate heart-shaped QR code with better heart shape"""
        url = request.build_absolute_uri(self.get_absolute_url())
        
        # Create QR code with higher version for better resolution
        qr = qrcode.QRCode(version=3, box_size=8, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        size = qr_img.size[0]
        
        # Create heart mask with better heart shape
        heart_mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(heart_mask)
        
        center_x, center_y = size // 2, size // 2
        scale = size // 6
        
        # Better heart equation
        for y in range(size):
            for x in range(size):
                # Normalize coordinates
                nx = (x - center_x) / scale
                ny = (center_y - y) / scale - 0.5
                
                # Heart equation: (x²+y²-1)³ ≤ x²y³
                left_side = (nx*nx + ny*ny - 1)**3
                right_side = nx*nx * ny*ny*ny
                
                if left_side <= right_side and ny >= -1.5:
                    draw.point((x, y), fill=255)
        
        # Apply heart mask to QR code
        result = Image.new('RGBA', qr_img.size, (255, 255, 255, 0))
        qr_array = list(qr_img.getdata())
        mask_array = list(heart_mask.getdata())
        
        new_data = []
        for i in range(len(qr_array)):
            if mask_array[i] > 0:
                new_data.append(qr_array[i])
            else:
                new_data.append((255, 255, 255, 0))
        
        result.putdata(new_data)
        
        # Add romantic border
        bordered = Image.new('RGBA', (size + 40, size + 40), (255, 182, 193, 100))
        bordered.paste(result, (20, 20))
        
        # Convert to base64
        buffer = io.BytesIO()
        bordered.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

class Message(models.Model):
    page = models.ForeignKey(MessagePage, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField()
    order = models.IntegerField(default=0)
    font_size = models.IntegerField(default=32)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']

class MessageTemplate(models.Model):
    """Pre-defined message templates for inspiration"""
    name = models.CharField(max_length=100)
    messages = models.JSONField(default=list)  # List of message strings
    category = models.CharField(max_length=50, choices=[
        ('romantic', 'Romantic'),
        ('anniversary', 'Anniversary'),
        ('proposal', 'Proposal'),
        ('birthday', 'Birthday'),
        ('general', 'General Love')
    ])
    is_active = models.BooleanField(default=True)