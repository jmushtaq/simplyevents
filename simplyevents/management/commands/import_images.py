import os
import random
from django.core.management.base import BaseCommand
from django.core.files import File
from oscar.apps.catalogue.models import ProductImage

class Command(BaseCommand):
    help = 'Import product images from party images directory'

    def handle(self, *args, **options):
        source_dir = '/home/ubuntu/Downloads/party images/party images'
        media_dir = '/home/ubuntu/projects/simplyevents/media'
        image_extensions = ('.jpg', '.jpeg')

        files = [f for f in os.listdir(source_dir) 
                if f.lower().endswith(image_extensions)]

        if not files:
            self.stdout.write(self.style.WARNING('No image files found'))
            return

        self.stdout.write(f'Found {len(files)} image files')

        images = ProductImage.objects.filter(original='')
        self.stdout.write(f'Products needing images: {images.count()}')

        for i, img in enumerate(images):
            chosen = random.choice(files)
            src_path = os.path.join(source_dir, chosen)
            
            with open(src_path, 'rb') as f:
                filename = f'{img.product.slug}_{os.path.basename(chosen)}'
                img.original.save(filename, File(f), save=True)
                self.stdout.write(f'  {img.product.title}: {filename}')

        self.stdout.write(self.style.SUCCESS('Done!'))
