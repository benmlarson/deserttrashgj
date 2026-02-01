from django import forms

from .models import Submission

ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


class SubmissionForm(forms.ModelForm):
    latitude = forms.FloatField(widget=forms.HiddenInput, required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Submission
        fields = ["photo", "category", "severity", "description"]
        widgets = {
            "photo": forms.ClearableFileInput(
                attrs={"accept": "image/*", "capture": "environment"}
            ),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            return photo
        if photo.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Photo must be under 20 MB.")
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError(
                "Unsupported file type. Please upload a JPEG, PNG, or WebP image."
            )
        return photo
