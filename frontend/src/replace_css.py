import re
import sys

def replace_colors(content):
    # Mapping of regex patterns to replacements. Use \b or proper escaping
    replacements = [
        (r'rgba\(11,\s*13,\s*20,\s*0\.94\)', r'var(--bg-header)'),
        (r'rgba\(24,\s*27,\s*38,\s*0\.96\)', r'var(--bg-header)'),
        (r'rgba\(255,\s*255,\s*255,\s*0\.03\)', r'var(--bg-hover-subtle)'),
        (r'#0b0d14', r'var(--bg-page)'),
        (r'#171a24', r'var(--bg-card)'),
        (r'#181b26', r'var(--bg-card-alt)'),
        (r'#10131c', r'var(--bg-input)'),
        (r'#252938', r'var(--border-primary)'),
        (r'#303548', r'var(--border-primary)'),
        (r'#2b3040', r'var(--border-primary)'),
        (r'#272c3b', r'var(--border-primary)'),
        (r'#2d3345', r'var(--border-secondary)'),
        (r'#343a4d', r'var(--border-input)'),
        (r'#454b62', r'var(--border-input)'),
        (r'#f5f5f7', r'var(--text-heading)'),
        (r'#f4f5f7', r'var(--text-heading)'),
        (r'#ffffff', r'var(--text-heading)'),
        (r'#f8fafc', r'var(--text-body)'),
        (r'#9ca3af', r'var(--text-secondary)'),
        (r'#a7adbd', r'var(--text-subtle)'),
        (r'#9da4b5', r'var(--text-subtle)'),
        (r'#aeb4c5', r'var(--text-info)'),
        (r'#6b7280', r'var(--text-muted)'),
        (r'#e5e7eb', r'var(--text-label)'),
        (r'#e9eaf0', r'var(--text-label)'),
        (r'#747b8d', r'var(--text-placeholder)'),
        (r'#f1f2f5', r'var(--review-username)'),
        (r'#c0c5d2', r'var(--review-text)'),
        (r'#818cf8', r'var(--accent-text)'),
        (r'#8b7cf6', r'var(--accent-text)'),
        (r'#a78bfa', r'var(--accent-hover)'),
        (r'#a5b4fc', r'var(--accent-hover)'),
        (r'#fbbf24', r'var(--rating-color)'),
        (r'rgba\(99,\s*102,\s*241,\s*0\.12\)', r'var(--accent-glow)'),
        (r'rgba\(99,\s*102,\s*241,\s*0\.15\)', r'var(--accent-glow-strong)'),
        (r'rgba\(99,\s*102,\s*241,\s*0\.14\)', r'var(--accent-glow-focus)'),
        (r'rgba\(99,\s*102,\s*241,\s*0\.13\)', r'var(--accent-subtle-bg)'),
        (r'rgba\(99,\s*102,\s*241,\s*0\.08\)', r'var(--accent-gradient-bg)'),
        (r'rgba\(139,\s*92,\s*246,\s*0\.08\)', r'var(--purple-glow)'),
        (r'rgba\(139,\s*92,\s*246,\s*0\.12\)', r'var(--purple-glow-strong)'),
        (r'rgba\(139,\s*92,\s*246,\s*0\.04\)', r'var(--purple-gradient-bg)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.15\)', r'var(--shadow-sm)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.18\)', r'var(--shadow-md)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.3\)', r'var(--shadow-lg)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.45\)', r'var(--shadow-xl)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.25\)', r'var(--shadow-card-hover)'),
        (r'rgba\(239,\s*68,\s*68,\s*0\.1\)', r'var(--error-bg)'),
        (r'rgba\(239,\s*68,\s*68,\s*0\.08\)', r'var(--error-bg)'),
        (r'rgba\(239,\s*68,\s*68,\s*0\.25\)', r'var(--error-border)'),
        (r'rgba\(239,\s*68,\s*68,\s*0\.3\)', r'var(--error-border)'),
        (r'rgba\(239,\s*68,\s*68,\s*0\.35\)', r'var(--error-border)'),
        (r'#f87171', r'var(--error-text)'),
        (r'rgba\(34,\s*197,\s*94,\s*0\.1\)', r'var(--success-bg)'),
        (r'rgba\(34,\s*197,\s*94,\s*0\.3\)', r'var(--success-border)'),
        (r'#4ade80', r'var(--success-text)'),
        (r'#22c55e', r'var(--pw-valid)'),
        (r'#ef4444', r'var(--pw-invalid)'),
        (r'#cbd5e1', r'var(--pw-title)'),
        (r'rgba\(0,\s*0,\s*0,\s*0\.4\)', r'var(--shadow-xl)')
    ]
    
    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content, flags=re.IGNORECASE)

    # Note: the gradient is linear-gradient(135deg, #6366f1, #8b5cf6), this should not be touched as they use --accent?
    # Actually wait! If we replaced #6366f1 with var(--accent), that is correct. Wait, the user said:
    # "Keep the gradient for buttons (`linear-gradient(135deg, #6366f1, #8b5cf6)`) — accent colors stay the same in both themes"
    # "Keep `rgba(99, 102, 241, 0.3)` or `0.35` button hover shadows — accent glows stay"
    # "Keep `color: white` on buttons with gradient backgrounds — that's always white text on indigo"
    
    theme_toggle_css = """
/* Theme Toggle Button */
.theme-toggle {
  width: 44px;
  height: 44px;
  border: 1px solid var(--border-input);
  border-radius: 12px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: 0.2s ease;
  flex-shrink: 0;
}

.theme-toggle:hover {
  border-color: var(--accent);
  color: var(--accent-text);
  transform: translateY(-2px);
}

"""
    # Insert theme_toggle_css before the first @media query
    if "@media" in content:
        content = content.replace("@media", theme_toggle_css + "@media", 1)
    else:
        content += "\n" + theme_toggle_css
        
    return content

if __name__ == "__main__":
    with open("App.css", "r", encoding="utf-8") as f:
        content = f.read()
    new_content = replace_colors(content)
    with open("App.css", "w", encoding="utf-8") as f:
        f.write(new_content)
