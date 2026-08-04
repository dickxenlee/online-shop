"""Cloudinary-backed Django storage used only when CLOUDINARY_URL is set."""
from cloudinary.uploader import destroy, upload
from cloudinary.utils import cloudinary_url
from django.core.files.storage import Storage


class CloudinaryMediaStorage(Storage):
    """Store product uploads in Cloudinary instead of Render's local disk."""

    def _save(self, name, content):
        result = upload(
            content,
            folder='meiyi',
            resource_type='image',
            use_filename=True,
            unique_filename=True,
        )
        return result['public_id']

    def exists(self, name):
        # Cloudinary creates a unique public id for every upload.
        return False

    def url(self, name):
        return cloudinary_url(name, resource_type='image', secure=True)[0]

    def delete(self, name):
        destroy(name, resource_type='image', invalidate=True)
