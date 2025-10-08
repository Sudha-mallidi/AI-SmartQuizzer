from django import forms
from .models import StudyMaterial,Topic,SubTopic

class StudyMaterialForm(forms.ModelForm):
    topic = forms.CharField(
        max_length=200,
        label="Topic",
        widget=forms.TextInput(attrs={'placeholder': 'Enter topic'})
    )
    subtopic = forms.CharField(
        max_length=200,
        label="Subtopic",
        widget=forms.TextInput(attrs={'placeholder': 'Enter subtopic'})
    )
    difficulty_level = forms.ChoiceField(
        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
        label="Difficulty Level"
    )
    document = forms.FileField(label="Upload PDF")

    class Meta:
        model = StudyMaterial
        fields = ['difficulty_level', 'document']

    def save(self, commit=True):
        # get typed values
        topic_name = self.cleaned_data.get('topic')
        subtopic_name = self.cleaned_data.get('subtopic')

        # fetch or create Topic/SubTopic
        topic_obj, _ = Topic.objects.get_or_create(name=topic_name)
        subtopic_obj, _ = SubTopic.objects.get_or_create(name=subtopic_name, topic=topic_obj)

        # assign back to instance
        instance = super().save(commit=False)
        instance.topic = topic_obj
        instance.subtopic = subtopic_obj

        if commit:
            instance.save()
        return instance
