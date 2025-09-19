from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(is_safe=True)
def format_product_description(value):
    """
    Format product description text with proper HTML rendering.
    Converts line breaks, bullet points, and other formatting to HTML.
    """
    if not value:
        return ""
    
    # Convert the text to HTML
    html = str(value)
    
    # Split into lines first
    lines = html.split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            formatted_lines.append('')  # Empty line
            continue
            
        # Check for bullet points
        if (line.startswith('•') or line.startswith('-') or line.startswith('*')) and len(line) > 1:
            if not in_list:
                formatted_lines.append('<ul>')
                in_list = True
            # Remove the bullet point and add as list item
            content = line[1:].strip()
            formatted_lines.append(f'<li>{content}</li>')
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            formatted_lines.append(line)
    
    # Close any remaining list
    if in_list:
        formatted_lines.append('</ul>')
    
    # Join lines with <br> tags, but handle empty lines and list items properly
    result_lines = []
    for i, line in enumerate(formatted_lines):
        if line == '':
            # Only add <br> if it's not the last line and not between list items
            if i < len(formatted_lines) - 1:
                result_lines.append('<br>')
        elif line.startswith('<ul>') or line.startswith('</ul>') or line.startswith('<li>'):
            # List items don't need <br> tags
            result_lines.append(line)
        else:
            # Regular text lines
            result_lines.append(line)
            if i < len(formatted_lines) - 1:
                result_lines.append('<br>')
    
    html = ''.join(result_lines)
    
    # Handle bold text (text between **)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Handle italic text (text between *)
    html = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', html)
    
    # Clean up multiple consecutive <br> tags
    html = re.sub(r'(<br>\s*){3,}', '<br><br>', html)
    
    return mark_safe(html)
