from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, login as auth_login
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages as dj_messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
import json
import qrcode
import io
import base64
from PIL import Image, ImageDraw
import logging

from .models import MessagePage, Message, MessageTemplate

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            dj_messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
        else:
            dj_messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            dj_messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            dj_messages.error(request, "Login failed. Please check your username and password.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def dashboard(request):
    try:
        pages = MessagePage.objects.filter(user=request.user).order_by('-updated_at')
        print(f"User {request.user.username} has {pages.count()} pages.")

        paginator = Paginator(pages, 9)  # Show 9 pages per page

        page_number = request.GET.get('page')
        if page_number is not None:
            try:
                page_number = int(page_number)
                if page_number < 1 or page_number > paginator.num_pages:
                    raise ValueError("Page number out of range")
            except (ValueError, TypeError) as e:
                print(f"Invalid page number '{page_number}': {e}. Defaulting to page 1.")
                page_number = 1
        else:
            page_number = 1

        page_obj = paginator.get_page(page_number)
        print(f"Displaying page {page_number} with {len(page_obj.object_list)} pages.")

        context = {'pages': MessagePage.objects.filter(user=request.user)}
        
        return render(request, 'dashboard.html', context)

    except Exception as e:
        print(f"Unexpected error in dashboard view: {e}")
        return render(request, 'dashboard.html', {'page_obj': None, 'error': 'An error occurred while loading your dashboard.'})


@login_required
def create_page(request):
    templates = MessageTemplate.objects.filter(is_active=True)
    
    if request.method == 'POST':
        title = request.POST.get('title', 'Love Messages')
        text_color = request.POST.get('text_color', '#FF69B4')
        background_color = request.POST.get('background_color', '#000000')
        template_id = request.POST.get('template')
        
        page = MessagePage.objects.create(
            user=request.user,
            title=title,
            text_color=text_color,
            background_color=background_color
        )
        
        # Add template messages if selected
        if template_id:
            try:
                template = MessageTemplate.objects.get(id=template_id)
                for i, msg_text in enumerate(template.messages):
                    Message.objects.create(
                        page=page,
                        text=msg_text,
                        order=i
                    )
            except MessageTemplate.DoesNotExist:
                pass
        
        return redirect('edit_page', page_id=page.id)
    
    return render(request, 'create_page.html', {'templates': templates})

def remove_whiteBG(image):
    """Remove white background from an image and make it transparent"""
    datas = image.getdata()
    newData = []
    for item in datas:
        # Change all white (also shades of whites)
        # pixels to transparent
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    image.putdata(newData)
    return image
    

def generate_heart_qr_code(url):
    """Generate a heart-shaped QR code with rotated QR and semi-circles, transparent QR background"""

    # Create QR code with high error correction
    qr = qrcode.QRCode(
        version=6,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=1
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create base QR code image with red fill and white background
    qr_img = qr.make_image(fill_color="red", back_color="white").convert("RGBA")
    qr_img = remove_whiteBG(qr_img)  # Remove white background
    qr_size = qr_img.size[0]

    # Create semi-circular QR code masks
    mask_left = Image.new("L", (qr_size, qr_size), 0)
    draw_left = ImageDraw.Draw(mask_left)
    draw_left.pieslice([0, 0, qr_size, qr_size], 90, 270, fill=255)  # Left semi-circle

    mask_right = Image.new("L", (qr_size, qr_size), 0)
    draw_right = ImageDraw.Draw(mask_right)
    draw_right.pieslice([0, 0, qr_size, qr_size], 270, 90, fill=255)  # Right semi-circle

    # Apply masks to QR code to get left and right semi-circular QR lobes
    qr_left = qr_img.copy()
    qr_left.putalpha(mask_left)
    qr_left = remove_whiteBG(qr_left)  # Ensure transparency

    qr_right = qr_img.copy()
    qr_right.putalpha(mask_right)
    qr_right = remove_whiteBG(qr_right)  # Ensure transparency

    # Rotate the QR lobes
    qr_left = qr_left.rotate(-45, expand=False, fillcolor=(255, 255, 255, 0))
    qr_right = qr_right.rotate(45, expand=False, fillcolor=(255, 255, 255, 0))

    # Rotate QR code 45 degrees for the bottom
    rotated_qr = qr_img.rotate(45, expand=True, fillcolor=(255, 255, 255, 0))
    rotated_size = rotated_qr.size[0]

    # Create heart shape components
    heart_width = rotated_size + qr_size  # Space for QR + semi-circles
    heart_height = rotated_size + qr_size // 2  # Height for the heart

    # Create the final heart image
    heart_img = Image.new('RGBA', (heart_width, heart_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(heart_img)

    # Position the rotated QR code in the center-bottom of the heart
    qr_x = (heart_width - rotated_size) // 2
    qr_y = heart_height - rotated_size - 10

    # Paste the rotated QR code (now with transparent background)
    heart_img.paste(rotated_qr, (qr_x, qr_y), rotated_qr)

    # Calculate positions for the semi-circular QR codes
    radius = qr_size // 2
    center_x = heart_width // 2
    vertical_offset = (radius // 2) + 40
    # horizontal_offset = floor((radius // 2) // PI) 
    horizontal_offset = int(radius // 6.30)  # Approximation of horizontal offset
    print(f"Heart dimensions: {heart_width}x{heart_height}, QR size: {qr_size}, radius: {radius}")
    
    # Left semi-circular QR position
    left_center_x = center_x - radius // 2 - horizontal_offset #32
    left_center_y = qr_y + vertical_offset
    left_qr_x = left_center_x - radius
    left_qr_y = left_center_y - radius
    
    # Right semi-circular QR position
    right_center_x = center_x + radius // 2 + horizontal_offset #32
    right_center_y = qr_y + vertical_offset
    right_qr_x = right_center_x - radius
    right_qr_y = right_center_y - radius

    # Paste the semi-circular QR codes at the calculated positions
    heart_img.paste(qr_left, (left_qr_x, left_qr_y), qr_left)
    heart_img.paste(qr_right, (right_qr_x, right_qr_y), qr_right)

    # Add a romantic border
    border_size = 15
    bordered_img = Image.new('RGBA', 
                            (heart_width + border_size * 2, heart_height + border_size * 2), 
                            (255, 182, 193, 100))  # Light pink border
    bordered_img.paste(heart_img, (border_size, border_size), heart_img)
    
    # Convert to base64
    buffered = io.BytesIO()
    bordered_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Return base64 string for embedding in HTML    
    return f"data:image/png;base64,{img_str}"

@login_required
def edit_page(request, page_id):
    page = get_object_or_404(MessagePage, id=page_id, user=request.user)
    
    if request.method == 'POST':
        # Handle AJAX save request
        if request.headers.get('Content-Type') == 'application/json':
            data = json.loads(request.body)
            page.title = data.get('title', page.title)
            page.text_color = data.get('text_color', page.text_color)
            page.background_color = data.get('background_color', page.background_color)
            page.animation_speed = float(data.get('animation_speed', page.animation_speed))
            page.save()
            return JsonResponse({'success': True, 'message': 'Page saved successfully!'})
        
        # Handle regular form submission
        page.title = request.POST.get('title', page.title)
        page.text_color = request.POST.get('text_color', page.text_color)
        page.background_color = request.POST.get('background_color', page.background_color)
        page.animation_speed = float(request.POST.get('animation_speed', page.animation_speed))
        page.save()
        dj_messages.success(request, 'Page updated successfully!')
        return redirect('edit_page', page_id=page.id)
    
    # Generate QR code
    view_url = request.build_absolute_uri(reverse('view_page', args=[page.id]))
    print(f"Generating QR code for page {page.id} with URL: {view_url}")
    qr_code = generate_heart_qr_code(view_url)
    
    return render(request, 'edit_page.html', {
        'page': page,
        'qr_code': qr_code,
        'messages': page.messages.all().order_by('order', 'id')
    })

def view_page(request, page_id):
    page = get_object_or_404(MessagePage, id=page_id)
    
    # Increment view count
    page.view_count = (page.view_count or 0) + 1
    page.save(update_fields=['view_count'])
    
    messages_list = list(page.messages.values_list('text', flat=True).order_by('order', 'id'))
    
    return render(request, 'view_page.html', {
        'page': page,
        'messages_json': json.dumps(messages_list)
    })

# Set up logging
logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
def add_message(request, page_id):
    if request.method == 'POST':
        page = get_object_or_404(MessagePage, id=page_id, user=request.user)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        
        # Check for required 'text' field
        if 'text' not in data or not data['text'].strip():
            return JsonResponse({'success': False, 'error': 'Text field is required'}, status=400)
        
        Message.objects.create(
            page=page,
            text=data['text'],
            order=data.get('order', 0)
        )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=405)
    
@csrf_exempt
@login_required
def update_message(request, message_id):
    """Update an existing message"""
    if request.method == 'POST':
        message = get_object_or_404(Message, id=message_id, page__user=request.user)
        data = json.loads(request.body)
        
        message.text = data.get('text', message.text)
        message.font_size = data.get('font_size', message.font_size)
        message.save()
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'text': message.text
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def delete_message(request, message_id):
    if request.method == 'DELETE':
        try:
            message = get_object_or_404(Message, id=message_id, page__user=request.user)
            message.delete()
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False, 'error': 'Message not found or access denied'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def reorder_messages(request, page_id):
    """Reorder messages via drag and drop"""
    if request.method == 'POST':
        page = get_object_or_404(MessagePage, id=page_id, user=request.user)
        data = json.loads(request.body)
        message_ids = data.get('message_ids', [])
        
        # Update order for each message
        for index, message_id in enumerate(message_ids):
            Message.objects.filter(
                id=message_id, 
                page=page
            ).update(order=index)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@csrf_exempt
@login_required
def copy_messages(request):
    """Copy messages between pages"""
    if request.method == 'POST':
        data = json.loads(request.body)
        source_page_id = data.get('source_page_id')
        target_page_id = data.get('target_page_id')
        
        source_page = get_object_or_404(MessagePage, id=source_page_id, user=request.user)
        target_page = get_object_or_404(MessagePage, id=target_page_id, user=request.user)
        
        # Copy messages
        for message in source_page.messages.all():
            Message.objects.create(
                page=target_page,
                text=message.text,
                order=message.order,
                font_size=message.font_size
            )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
def page_analytics(request, page_id):
    """Simple analytics for page views"""
    page = get_object_or_404(MessagePage, id=page_id, user=request.user)
    
    context = {
        'page': page,
        'total_views': page.view_count or 0,
        'total_messages': page.messages.count(),
        'created_days_ago': (timezone.now() - page.created_at).days
    }
    
    return render(request, 'analytics.html', context)

@login_required
def duplicate_page(request, page_id):
    """Duplicate an existing page"""
    original_page = get_object_or_404(MessagePage, id=page_id, user=request.user)
    
    # Create new page
    new_page = MessagePage.objects.create(
        user=request.user,
        title=f"{original_page.title} (Copy)",
        text_color=original_page.text_color,
        background_color=original_page.background_color,
        animation_speed=original_page.animation_speed
    )
    
    # Copy all messages
    for message in original_page.messages.all():
        Message.objects.create(
            page=new_page,
            text=message.text,
            order=message.order,
            font_size=message.font_size
        )
    
    dj_messages.success(request, f'Page duplicated successfully!')
    return redirect('edit_page', page_id=new_page.id)

@login_required
def delete_page(request, page_id):
    """Delete a page"""
    if request.method == 'POST':
        page = get_object_or_404(MessagePage, id=page_id, user=request.user)
        page_title = page.title
        page.delete()
        dj_messages.success(request, f'Page "{page_title}" deleted successfully!')
        return redirect('dashboard')
    
    return redirect('dashboard')

@login_required
def preview_page(request, page_id):
    """Preview page in a modal or new tab"""
    page = get_object_or_404(MessagePage, id=page_id, user=request.user)
    messages_list = list(page.messages.values_list('text', flat=True).order_by('order', 'id'))
    
    # Don't increment view count for preview
    return render(request, 'view_page.html', {  # Changed from 'preview_page.html'
        'page': page,
        'messages_json': json.dumps(messages_list),
        'is_preview': True
    })