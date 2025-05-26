import json
import base64
from unittest.mock import patch, MagicMock
from io import BytesIO

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.messages import get_messages
from django.core.serializers.json import DjangoJSONEncoder

from .models import MessagePage, Message, MessageTemplate


# Run all tests
# python manage.py test love_messages.tests

# # Run specific test class
# python manage.py test love_messages.tests.ViewsTestCase

# # Run with coverage
# coverage run --source='.' manage.py test love_messages.tests
# coverage report

class ViewsTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            email='test@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpassword123'
        )
        
        # Create test message page
        self.message_page = MessagePage.objects.create(
            user=self.user,
            title='Test Love Messages',
            text_color='#FF69B4',
            background_color='#000000',
            animation_speed=2.0,
            view_count=5
        )
        
        # Create test messages
        self.message1 = Message.objects.create(
            page=self.message_page,
            text='I love you',
            order=0,
            font_size=16
        )
        self.message2 = Message.objects.create(
            page=self.message_page,
            text='You are amazing',
            order=1,
            font_size=18
        )
        
        # Create message template
        self.template = MessageTemplate.objects.create(
            name='Romantic Template',
            messages=['I love you', 'You are my world', 'Forever yours'],
            category='romantic',
            is_active=True
        )

    def test_register_get(self):
        """Test GET request to register view"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

    def test_register_post_valid(self):
        """Test POST request to register view with valid data"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_post_invalid(self):
        """Test POST request to register view with invalid data"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'password123',
            'password2': 'differentpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stay on register page
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_dashboard_authenticated(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Love Messages')
        self.assertIn('pages', response.context)

    def test_dashboard_unauthenticated(self):
        """Test dashboard view redirects unauthenticated users"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_pagination(self):
        """Test dashboard pagination"""
        self.client.login(username='testuser', password='testpassword123')
        
        # Create multiple pages to test pagination
        for i in range(15):
            MessagePage.objects.create(
                user=self.user,
                title=f'Page {i}',
                text_color='#FF0000',
                background_color='#000000'
            )
        
        response = self.client.get(reverse('dashboard') + '?page=2')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_invalid_page_number(self):
        """Test dashboard with invalid page number"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('dashboard') + '?page=invalid')
        self.assertEqual(response.status_code, 200)  # Should default to page 1

    def test_create_page_get(self):
        """Test GET request to create page view"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('create_page'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('templates', response.context)
        self.assertTrue(response.context['templates'].exists())

    def test_create_page_post_without_template(self):
        """Test POST request to create page without template"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('create_page'), {
            'title': 'New Page',
            'text_color': '#FF0000',
            'background_color': '#FFFFFF'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect to edit page
        new_page = MessagePage.objects.get(title='New Page')
        self.assertEqual(new_page.user, self.user)
        self.assertEqual(new_page.text_color, '#FF0000')

    def test_create_page_post_with_template(self):
        """Test POST request to create page with template"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('create_page'), {
            'title': 'Templated Page',
            'text_color': '#FF0000',
            'background_color': '#FFFFFF',
            'template': self.template.id
        })
        
        self.assertEqual(response.status_code, 302)
        new_page = MessagePage.objects.get(title='Templated Page')
        self.assertEqual(new_page.messages.count(), 3)  # Template has 3 messages

    def test_create_page_post_invalid_template(self):
        """Test POST request with invalid template ID"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('create_page'), {
            'title': 'Invalid Template Page',
            'template': 99999  # Non-existent template
        })
        
        self.assertEqual(response.status_code, 302)
        new_page = MessagePage.objects.get(title='Invalid Template Page')
        self.assertEqual(new_page.messages.count(), 0)  # No messages added

    @patch('love_messages.views.generate_heart_qr_code')
    def test_edit_page_get(self, mock_qr):
        """Test GET request to edit page view"""
        mock_qr.return_value = 'data:image/png;base64,fake_qr_code'
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.get(reverse('edit_page', args=[self.message_page.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'], self.message_page)
        self.assertIn('qr_code', response.context)
        self.assertEqual(len(response.context['messages']), 2)

    def test_edit_page_post_form(self):
        """Test POST request to edit page via form"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('edit_page', args=[self.message_page.id]), {
            'title': 'Updated Title',
            'text_color': '#00FF00',
            'background_color': '#FFFF00',
            'animation_speed': '3.5'
        })
        
        self.assertEqual(response.status_code, 302)
        self.message_page.refresh_from_db()
        self.assertEqual(self.message_page.title, 'Updated Title')
        self.assertEqual(self.message_page.text_color, '#00FF00')
        self.assertEqual(self.message_page.animation_speed, 3.5)

    def test_edit_page_post_ajax(self):
        """Test POST request to edit page via AJAX"""
        self.client.login(username='testuser', password='testpassword123')
        data = {
            'title': 'AJAX Updated Title',
            'text_color': '#0000FF',
            'background_color': '#FF00FF',
            'animation_speed': '1.5'
        }
        
        response = self.client.post(
            reverse('edit_page', args=[self.message_page.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        self.message_page.refresh_from_db()
        self.assertEqual(self.message_page.title, 'AJAX Updated Title')

    def test_edit_page_unauthorized(self):
        """Test edit page access by unauthorized user"""
        self.client.login(username='otheruser', password='otherpassword123')
        response = self.client.get(reverse('edit_page', args=[self.message_page.id]))
        self.assertEqual(response.status_code, 404)

    def test_view_page(self):
        """Test view page functionality"""
        initial_view_count = self.message_page.view_count
        response = self.client.get(reverse('view_page', args=[self.message_page.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'], self.message_page)
        
        # Check view count incremented
        self.message_page.refresh_from_db()
        self.assertEqual(self.message_page.view_count, initial_view_count + 1)
        
        # Check messages JSON
        messages_json = json.loads(response.context['messages_json'])
        self.assertEqual(len(messages_json), 2)
        self.assertIn('I love you', messages_json)

    def test_view_page_nonexistent_fixed(self):
        """Test view page with non-existent page ID"""
        import uuid
        fake_uuid = uuid.uuid4()
        response = self.client.get(reverse('view_page', args=[fake_uuid]))
        self.assertEqual(response.status_code, 404)

    def test_add_message(self):
        """Test adding a message to a page"""
        self.client.login(username='testuser', password='testpassword123')
        data = {'text': 'New message', 'order': 2}
        
        response = self.client.post(
            reverse('add_message', args=[self.message_page.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check message was created
        new_message = Message.objects.get(text='New message')
        self.assertEqual(new_message.page, self.message_page)
        self.assertEqual(new_message.order, 2)

    def test_add_message_unauthorized(self):
        """Test adding message to unauthorized page"""
        self.client.login(username='otheruser', password='otherpassword123')
        data = {'text': 'Unauthorized message'}
        
        response = self.client.post(
            reverse('add_message', args=[self.message_page.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)

    def test_add_message_get_request(self):
        """Test GET request to add message (should fail)"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('add_message', args=[self.message_page.id]))
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_update_message(self):
        """Test updating an existing message"""
        self.client.login(username='testuser', password='testpassword123')
        data = {'text': 'Updated message text', 'font_size': 20}
        
        response = self.client.post(
            reverse('update_message', args=[self.message1.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        self.message1.refresh_from_db()
        self.assertEqual(self.message1.text, 'Updated message text')
        self.assertEqual(self.message1.font_size, 20)

    def test_update_message_unauthorized(self):
        """Test updating message by unauthorized user"""
        self.client.login(username='otheruser', password='otherpassword123')
        data = {'text': 'Hacked message'}
        
        response = self.client.post(
            reverse('update_message', args=[self.message1.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)

    def test_delete_message(self):
        """Test deleting a message"""
        self.client.login(username='testuser', password='testpassword123')
        message_id = self.message1.id
        
        response = self.client.delete(reverse('delete_message', args=[message_id]))
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check message was deleted
        self.assertFalse(Message.objects.filter(id=message_id).exists())

    def test_delete_message_unauthorized(self):
        """Test deleting message by unauthorized user"""
        self.client.login(username='otheruser', password='otherpassword123')
        
        response = self.client.delete(reverse('delete_message', args=[self.message1.id]))
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        
        # Check message still exists
        self.assertTrue(Message.objects.filter(id=self.message1.id).exists())

    def test_reorder_messages(self):
        """Test reordering messages"""
        self.client.login(username='testuser', password='testpassword123')
        data = {'message_ids': [self.message2.id, self.message1.id]}
        
        response = self.client.post(
            reverse('reorder_messages', args=[self.message_page.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check order was updated
        self.message1.refresh_from_db()
        self.message2.refresh_from_db()
        self.assertEqual(self.message2.order, 0)
        self.assertEqual(self.message1.order, 1)

    def test_copy_messages(self):
        """Test copying messages between pages"""
        self.client.login(username='testuser', password='testpassword123')
        
        # Create target page
        target_page = MessagePage.objects.create(
            user=self.user,
            title='Target Page'
        )
        
        data = {
            'source_page_id': str(self.message_page.id),  # Convert UUID to string
            'target_page_id': str(target_page.id)         # Convert UUID to string
        }
        
        response = self.client.post(
            reverse('copy_messages'),
            json.dumps(data, cls=DjangoJSONEncoder),  # Use custom encoder
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check messages were copied
        self.assertEqual(target_page.messages.count(), 2)

    def test_copy_messages_unauthorized(self):
        """Test copying messages with unauthorized access"""
        self.client.login(username='otheruser', password='otherpassword123')
        
        target_page = MessagePage.objects.create(
            user=self.other_user,
            title='Other User Target Page'
        )
        
        data = {
            'source_page_id': str(self.message_page.id),  # Convert UUID to string
            'target_page_id': str(target_page.id)         # Convert UUID to string
        }
        
        response = self.client.post(
            reverse('copy_messages'),
            json.dumps(data, cls=DjangoJSONEncoder),  # Use custom encoder
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)

    def test_page_analytics(self):
        """Test page analytics view"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('page_analytics', args=[self.message_page.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'], self.message_page)
        self.assertEqual(response.context['total_views'], 5)
        self.assertEqual(response.context['total_messages'], 2)
        self.assertIn('created_days_ago', response.context)

    def test_duplicate_page(self):
        """Test duplicating a page"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('duplicate_page', args=[self.message_page.id]))
        
        self.assertEqual(response.status_code, 302)  # Redirect to edit new page
        
        # Check new page was created
        new_page = MessagePage.objects.filter(title='Test Love Messages (Copy)').first()
        self.assertIsNotNone(new_page)
        self.assertEqual(new_page.user, self.user)
        self.assertEqual(new_page.text_color, self.message_page.text_color)
        self.assertEqual(new_page.messages.count(), 2)

    def test_delete_page(self):
        """Test deleting a page"""
        self.client.login(username='testuser', password='testpassword123')
        page_id = self.message_page.id
        
        response = self.client.post(reverse('delete_page', args=[page_id]))
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        self.assertFalse(MessagePage.objects.filter(id=page_id).exists())

    def test_delete_page_get_request(self):
        """Test GET request to delete page (should redirect)"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('delete_page', args=[self.message_page.id]))
        
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        self.assertTrue(MessagePage.objects.filter(id=self.message_page.id).exists())

    def test_preview_page(self):
        """Test preview page functionality"""
        self.client.login(username='testuser', password='testpassword123')
        initial_view_count = self.message_page.view_count
        
        response = self.client.get(reverse('preview_page', args=[self.message_page.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'], self.message_page)
        self.assertTrue(response.context['is_preview'])
        
        # Check view count NOT incremented for preview
        self.message_page.refresh_from_db()
        self.assertEqual(self.message_page.view_count, initial_view_count)

    @patch('love_messages.views.qrcode.QRCode')
    @patch('love_messages.views.Image')
    def test_generate_heart_qr_code(self, mock_image, mock_qr_class):
        """Test QR code generation function"""
        # Mock QR code creation
        mock_qr = MagicMock()
        mock_qr_class.return_value = mock_qr
        
        # Mock image operations
        mock_img = MagicMock()
        mock_qr.make_image.return_value = mock_img
        mock_img.convert.return_value = mock_img
        mock_img.size = [200, 200]
        mock_img.copy.return_value = mock_img
        mock_img.rotate.return_value = mock_img
        
        mock_image.new.return_value = mock_img
        
        # Mock BytesIO for base64 conversion
        with patch('love_messages.views.io.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_bytesio.return_value = mock_buffer
            mock_buffer.getvalue.return_value = b'fake_image_data'
            
            from .views import generate_heart_qr_code
            result = generate_heart_qr_code('http://example.com')
            
            self.assertTrue(result.startswith('data:image/png;base64,'))
            mock_qr.add_data.assert_called_with('http://example.com')
            mock_qr.make.assert_called_with(fit=True)


class IntegrationTestCase(TestCase):
    """Integration tests for complete user workflows"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='integrationuser',
            password='testpass123'
        )

    def test_complete_page_creation_workflow(self):
        """Test complete workflow from login to page creation to viewing"""
        # Login
        self.client.login(username='integrationuser', password='testpass123')
        
        # Create page
        response = self.client.post(reverse('create_page'), {
            'title': 'Integration Test Page',
            'text_color': '#FF0000',
            'background_color': '#000000'
        })
        
        # Get the created page
        page = MessagePage.objects.get(title='Integration Test Page')
        
        # Add messages
        self.client.post(
            reverse('add_message', args=[page.id]),
            json.dumps({'text': 'First message', 'order': 0}),
            content_type='application/json'
        )
        
        self.client.post(
            reverse('add_message', args=[page.id]),
            json.dumps({'text': 'Second message', 'order': 1}),
            content_type='application/json'
        )
        
        # View the page
        response = self.client.get(reverse('view_page', args=[page.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check messages are in the context
        messages_json = json.loads(response.context['messages_json'])
        self.assertEqual(len(messages_json), 2)
        self.assertIn('First message', messages_json)
        self.assertIn('Second message', messages_json)

    def test_message_management_workflow(self):
        """Test complete message management workflow"""
        self.client.login(username='integrationuser', password='testpass123')
        
        # Create page with messages
        page = MessagePage.objects.create(
            user=self.user,
            title='Message Management Test'
        )
        
        # Add messages
        msg1_response = self.client.post(
            reverse('add_message', args=[page.id]),
            json.dumps({'text': 'Original message', 'order': 0}),
            content_type='application/json'
        )
        
        # Get the message ID from database
        message = Message.objects.get(text='Original message')
        
        # Update message
        self.client.post(
            reverse('update_message', args=[message.id]),
            json.dumps({'text': 'Updated message', 'font_size': 20}),
            content_type='application/json'
        )
        
        # Verify update
        message.refresh_from_db()
        self.assertEqual(message.text, 'Updated message')
        self.assertEqual(message.font_size, 20)
        
        # Delete message
        self.client.delete(reverse('delete_message', args=[message.id]))
        
        # Verify deletion
        self.assertFalse(Message.objects.filter(id=message.id).exists())


class ErrorHandlingTestCase(TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='erroruser',
            password='testpass123'
        )

    def test_malformed_json_requests(self):
        """Test handling of malformed JSON requests"""
        self.client.login(username='erroruser', password='testpass123')
        
        page = MessagePage.objects.create(user=self.user, title='Test Page')
        
        response = self.client.post(
            reverse('add_message', args=[page.id]),
            'invalid json',
            content_type='application/json'
        )
        
        # Should handle gracefully (exact behavior depends on your error handling)
        self.assertIn(response.status_code, [400, 500])

    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        self.client.login(username='erroruser', password='testpass123')
        
        page = MessagePage.objects.create(user=self.user, title='Test Page')
        
        # Try to add message without text
        response = self.client.post(
            reverse('add_message', args=[page.id]),
            json.dumps({'order': 0}),  # Missing 'text' field
            content_type='application/json'
        )
        
        # Should handle gracefully
        response_data = json.loads(response.content)
        # Depending on your implementation, this might succeed with empty text or fail
        self.assertIn('success', response_data)

    def test_nonexistent_resource_access(self):
        """Test access to non-existent resources"""
        self.client.login(username='erroruser', password='testpass123')
        
        # Use a valid UUID format for non-existent page
        fake_uuid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        
        # Try to access non-existent page
        response = self.client.get(reverse('edit_page', args=[fake_uuid]))
        self.assertEqual(response.status_code, 404)
        
        # Try to update non-existent message (this uses int ID which is correct)
        response = self.client.post(
            reverse('update_message', args=[99999]),
            json.dumps({'text': 'New text'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)