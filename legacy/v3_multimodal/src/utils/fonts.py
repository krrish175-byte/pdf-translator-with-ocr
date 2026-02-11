from pathlib import Path
import logging

def get_cjk_font_path():
    """Finds a suitable CJK font on the system."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        # Add Linux/Windows paths if needed in future
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "C:\\Windows\\Fonts\\arialuni.ttf"
    ]
    
    for path in candidates:
        if Path(path).exists():
            return path
            
    return None
