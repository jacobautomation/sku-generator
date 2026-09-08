from django import template

register = template.Library()


@register.filter
def widget_class(field):
    return field.field.widget.__class__.__name__
