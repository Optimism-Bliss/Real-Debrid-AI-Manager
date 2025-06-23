import re
import logging
from .config import JAV_PREFIXES

logger = logging.getLogger(__name__)

def is_jav_prefix(name):
    """Check if folder name contains JAV prefix code."""
    # Multiple patterns to catch different formats
    patterns = [
        r'([A-Z0-9]{2,6})[-_](\d{3,5})',          # Standard: SONE-123, SONE_123
        r'([A-Z0-9]{2,6})\s+(\d{3,5})',          # With space: SONE 123, Sone 725
        r'([A-Z0-9]{2,6})(\d{3,5})',             # No separator: SONE123
        r'@([A-Z0-9]{2,6})[-_](\d{3,5})',        # With @: @SONE-123
        r'\.com@([A-Z0-9]{2,6})[-_\s](\d{3,5})', # Website format: 169bbs.com@SONE-564, 169bbs.com@sone 564
        r'([0-9]+bbs)\s+Com@([A-Z0-9]{2,6})[-_\s](\d{3,5})', # Special: 169bbs Com@sone 564
        r'([A-Z0-9]{2,6})[-_](\d{3,5})[-_\[]',   # With trailing separator: SONE-123_ or SONE-123[
        r'h[hd]d\d+\.com@([A-Z0-9]{2,6})[-_](\d{3,5})', # hhd800.com@START-296, hdd600.com@HUNTA-723
        r'([A-Z0-9]{2,6})[-_](\d{3,5})[a-z]+',   # With suffix: JUR-317ch, DASS-616ch
        r'([A-Z0-9]{2,6})[-_](\d{3,5})[-_]uncensored', # Uncensored format
        r'([A-Z0-9]{2,6})[-_](\d{3,5})\.TS',     # .TS format
        r'([A-Z0-9]{2,6})[-_](\d{3,5})_\[4K\]',  # _[4K] format
        r'\(Uncensored[^)]*\)\s*([A-Z0-9]{2,6})[-_](\d{3,5})', # (Uncensored Leaked) PREFIX-123
        r'([A-Z0-9]{2,6})[-_](\d{3,5})[^a-zA-Z0-9]', # Followed by non-alphanumeric
        
        # FC2-PPV specific patterns - CRITICAL FIX
        r'FC2[-_]PPV[-_](\d{4,7})',               # FC2-PPV-1234567
        r'fc2[-_]ppv[-_](\d{4,7})',               # fc2-ppv-1234567
        r'\.com@FC2[-_]PPV[-_](\d{4,7})',         # website.com@FC2-PPV-1234567
        r'\.com@fc2[-_]ppv[-_](\d{4,7})',         # website.com@fc2-ppv-1234567
        r'FC2[-_]PPV[-_](\d{4,7})[-_]',           # FC2-PPV-1234567-
        r'fc2[-_]ppv[-_](\d{4,7})[-_]',           # fc2-ppv-1234567-
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            # Extract the prefix and code
            groups = match.groups()
            if len(groups) >= 2:
                # Handle special case: 169bbs Com@sone 564 (3 groups)
                if len(groups) == 3 and 'bbs' in groups[0].lower():
                    prefix = groups[1]  # SONE
                    code = groups[2]    # 564
                else:
                    prefix = groups[0] if groups[0] else groups[1]  # Handle different group positions
                    code = groups[1] if groups[0] else groups[0]
                
                # Special handling for FC2-PPV
                if 'fc2' in pattern.lower():
                    prefix = 'FC2-PPV'
                    code = groups[-1]  # Last group is always the number for FC2
                
                if prefix.upper() in JAV_PREFIXES or 'FC2' in prefix.upper():
                    logger.info(f"JAV detected with pattern '{pattern}': {prefix}-{code} from {name}")
                    return True
            elif len(groups) == 1:
                # Single group patterns (like FC2-PPV)
                prefix = 'FC2-PPV' if 'fc2' in pattern.lower() else groups[0]
                if 'FC2' in prefix.upper():
                    logger.info(f"JAV detected (FC2-PPV): {name}")
                    return True
    
    # Fallback: Check if folder name starts with any known JAV prefix
    name_upper = name.upper()
    for prefix in JAV_PREFIXES:
        # Check exact prefix match at start
        if name_upper.startswith(prefix + '-') or name_upper.startswith(prefix + '_') or name_upper.startswith(prefix + ' '):
            logger.info(f"JAV detected (prefix match): {prefix} from {name}")
            return True
        # Check after website prefix
        if f'@{prefix}-' in name_upper or f'@{prefix}_' in name_upper:
            logger.info(f"JAV detected (website prefix): {prefix} from {name}")
            return True
    
    # Special check for FC2-PPV anywhere in the name
    if re.search(r'fc2[-_]?ppv', name, re.IGNORECASE):
        logger.info(f"JAV detected (FC2-PPV anywhere): {name}")
        return True
    
    return False

def extract_jav_code(name):
    """Extract JAV code from folder name."""
    # Patterns to extract JAV codes - same as detection but focused on extraction
    patterns = [
        # FC2-PPV patterns first (highest priority)
        r'FC2[-_]PPV[-_](\d{4,7})',               # FC2-PPV-1234567
        r'fc2[-_]ppv[-_](\d{4,7})',               # fc2-ppv-1234567
        r'\.com@FC2[-_]PPV[-_](\d{4,7})',         # website.com@FC2-PPV-1234567
        r'\.com@fc2[-_]ppv[-_](\d{4,7})',         # website.com@fc2-ppv-1234567
        r'FC2[-_]PPV[-_](\d{4,7})[-_]',           # FC2-PPV-1234567-
        r'fc2[-_]ppv[-_](\d{4,7})[-_]',           # fc2-ppv-1234567-
        
        # Standard JAV patterns
        r'([A-Z0-9]{2,6})[-_](\d{3,5})',          # Standard: SONE-123, SONE_123
        r'([A-Z0-9]{2,6})\s+(\d{3,5})',          # With space: SONE 123, Sone 725
        r'([A-Z0-9]{2,6})(\d{3,5})',             # No separator: SONE123
        r'@([A-Z0-9]{2,6})[-_](\d{3,5})',        # With @: @SONE-123
        r'\.com@([A-Z0-9]{2,6})[-_\s](\d{3,5})', # Website format: 169bbs.com@SONE-564, 169bbs.com@sone 564
        r'([0-9]+bbs)\s+Com@([A-Z0-9]{2,6})[-_\s](\d{3,5})', # Special: 169bbs Com@sone 564
        r'h[hd]d\d+\.com@([A-Z0-9]{2,6})[-_](\d{3,5})', # hhd800.com@START-296, hdd600.com@HUNTA-723
        r'([A-Z0-9]{2,6})[-_](\d{3,5})[a-z]+',   # With suffix: JUR-317ch, DASS-616ch
        r'([A-Z0-9]{2,6})[-_](\d{3,5})[-_]uncensored', # Uncensored format
        r'([A-Z0-9]{2,6})[-_](\d{3,5})\.TS',     # .TS format
        r'([A-Z0-9]{2,6})[-_](\d{3,5})_\[4K\]',  # _[4K] format
        r'\(Uncensored[^)]*\)\s*([A-Z0-9]{2,6})[-_](\d{3,5})', # (Uncensored Leaked) PREFIX-123
        r'([A-Z0-9]{2,6})[-_](\d{3,5})[^a-zA-Z0-9]', # Followed by non-alphanumeric
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            # Handle FC2-PPV patterns
            if 'fc2' in pattern.lower():
                code = groups[-1]  # Last group is always the number for FC2
                jav_code = f"FC2-PPV-{code}"
                logger.info(f"Extracted JAV code: {jav_code} from {name}")
                return jav_code
            
            # Handle standard JAV patterns
            elif len(groups) >= 2:
                # Handle special case: 169bbs Com@sone 564 (3 groups)
                if len(groups) == 3 and 'bbs' in groups[0].lower():
                    prefix = groups[1]  # SONE
                    code = groups[2]    # 564
                else:
                    prefix = groups[0] if groups[0] else groups[1]
                    code = groups[1] if groups[0] else groups[0]
                
                if prefix and prefix.upper() in JAV_PREFIXES:
                    # Always use standard format with dash
                    jav_code = f"{prefix.upper()}-{code}"
                    logger.info(f"Extracted JAV code: {jav_code} from {name}")
                    return jav_code
            
            # Single group patterns
            elif len(groups) == 1:
                code = groups[0]
                # Try to find prefix in the original name
                name_before_match = name[:match.start()]
                prefix_match = re.search(r'([A-Z0-9]{2,6})[-_]?$', name_before_match, re.IGNORECASE)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    if prefix.upper() in JAV_PREFIXES:
                        jav_code = f"{prefix.upper()}-{code}"
                        logger.info(f"Extracted JAV code: {jav_code} from {name}")
                        return jav_code
    
    # Fallback: Try to extract from start of name
    name_upper = name.upper()
    for prefix in JAV_PREFIXES:
        # Direct prefix match - handle space, dash, underscore
        if (name_upper.startswith(prefix + '-') or 
            name_upper.startswith(prefix + '_') or 
            name_upper.startswith(prefix + ' ')):
            code_match = re.search(rf'{re.escape(prefix)}[-_\s](\d{{3,7}})', name, re.IGNORECASE)
            if code_match:
                code = code_match.group(1)
                # Always use standard format with dash
                jav_code = f"{prefix}-{code}"
                logger.info(f"Extracted JAV code (fallback): {jav_code} from {name}")
                return jav_code
        
        # After website prefix
        website_pattern = rf'\.com@{re.escape(prefix)}[-_](\d{{3,7}})'
        website_match = re.search(website_pattern, name, re.IGNORECASE)
        if website_match:
            code = website_match.group(1)
            jav_code = f"{prefix}-{code}"
            logger.info(f"Extracted JAV code (website): {jav_code} from {name}")
            return jav_code
    
    # Special fallback for FC2-PPV anywhere
    fc2_match = re.search(r'fc2[-_]?ppv[-_]?(\d{4,7})', name, re.IGNORECASE)
    if fc2_match:
        code = fc2_match.group(1)
        jav_code = f"FC2-PPV-{code}"
        logger.info(f"Extracted JAV code (FC2 fallback): {jav_code} from {name}")
        return jav_code
    
    logger.warning(f"Could not extract JAV code from: {name}")
    return None 