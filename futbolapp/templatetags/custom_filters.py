from django import template

register = template.Library()

@register.filter
def startswith(value, arg):
    return value.startswith(arg)

@register.filter
def endswith(value, arg):
    return value.endswith(arg)