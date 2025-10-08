from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Return value from dictionary by key"""
    return dictionary.get(str(key))