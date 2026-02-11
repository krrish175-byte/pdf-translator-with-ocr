import yaml
import os
from typing import Dict, Any

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    default_config = {
        'translation': {
            'source_lang': 'en',
            'target_lang': 'ja',
            'api_provider': 'google',
            'api_key': os.getenv('TRANSLATION_API_KEY', '')
        },
        'ocr': {
            'engine': 'easyocr',
            'languages': ['en'],
            'gpu': False,
            'text_threshold': 0.7
        },
        'image_processing': {
            'dpi': 300,
            'contrast_enhance': True,
            'text_removal_method': 'inpaint',
            'font_size_scale': 0.9
        },
        'output': {
            'preserve_layout': True,
            'embed_japanese_fonts': True,
            'default_japanese_font': 'NotoSansJP'
        },
        'logging': {
            'level': 'INFO',
            'save_translation_log': True
        }
    }
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        
        # Merge with default config
        def merge_dicts(default, user):
            for key, value in user.items():
                if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                    merge_dicts(default[key], value)
                else:
                    default[key] = value
        
        merge_dicts(default_config, user_config)
    
    return default_config
