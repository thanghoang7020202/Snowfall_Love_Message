from django.core.management.base import BaseCommand
from love_messages.models import MessageTemplate

class Command(BaseCommand):
    help = 'Populate message templates'
    
    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Romantic Classic',
                'category': 'romantic',
                'messages': [
                    'I love you more than words can express',
                    'You are my sunshine on cloudy days',
                    'Every moment with you is a treasure',
                    'You make my heart skip a beat',
                    'Forever and always, my love'
                ]
            },
            {
                'name': 'Anniversary Special',
                'category': 'anniversary',
                'messages': [
                    'Another year of loving you',
                    'Our love grows stronger each day',
                    'Thank you for being my everything',
                    'Here\'s to many more years together',
                    'You are my greatest adventure'
                ]
            },
            {
                'name': 'Proposal Dreams',
                'category': 'proposal',
                'messages': [
                    'Will you marry me?',
                    'Be my forever',
                    'Let\'s write our love story together',
                    'You are my happily ever after',
                    'Say yes to forever with me'
                ]
            }
        ]
        
        for template_data in templates:
            MessageTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults={
                    'category': template_data['category'],
                    'messages': template_data['messages']
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated message templates')
        )