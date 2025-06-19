import os
import re
import json
import csv
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from collections import deque
from typing import Set, List, Union

# Android-safe emoji sets by categories
EMOJI_ANIMALS_NATURE = [
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
    "🦁", "🐮", "🐷", "🐸", "🐵", "🦄", "🐔", "🐧", "🐦", "🐤"
]
EMOJI_FOOD_DRINK = [
    "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐",
    "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑"
]
EMOJI_ACTIVITY = [
    "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏉", "🎱", "🏓", "🏸",
    "🥅", "🏒", "🏑", "🏏", "⛳", "🏹", "🎣", "🤿", "🥊", "🥋"
]
EMOJI_OBJECTS = [
    "⌚", "📱", "💻", "🖨️", "🕹️", "🎮", "📷", "📸", "📹", "🎥",
    "📺", "📻", "🎙️", "🎚️", "🎛️", "☎️", "📞", "📟", "📠", "🔋"
]
EMOJI_PLACES = [
    "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐",
    "🛻", "🚚", "🚛", "🚜", "🏍️", "🛵", "🚲", "🛴", "🚨", "🚔"
]

ANDROID_EMOJI_POOL = (
    EMOJI_ANIMALS_NATURE +
    EMOJI_FOOD_DRINK +
    EMOJI_ACTIVITY +
    EMOJI_OBJECTS +
    EMOJI_PLACES
)

# Regex pattern for emoji (wide, but not perfect!)
EMOJI_REGEX = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE
)

SUPPORTED_EXTS = (".json", ".txt", ".md", ".csv", ".xml", ".html", ".htm")

def extract_emojis(text: str) -> List[str]:
    return EMOJI_REGEX.findall(text)

def build_emoji_map(original_emojis: List[str], emoji_pool: List[str]) -> dict:
    """
    Map each original emoji (in order of appearance) to a replacement, cyclic by pool.
    The mapping is 1-to-1 and only for those emojis that existed in the original file.
    """
    emoji_map = dict()
    pool = deque(emoji_pool)
    for emoji in original_emojis:
        if emoji not in emoji_map:
            new_emoji = pool.popleft()
            emoji_map[emoji] = new_emoji
            pool.append(new_emoji)
    return emoji_map

def replace_emojis(text: str, emoji_map: dict) -> str:
    # Only replace emojis that exist in the original, keep positions unchanged.
    def replace_fn(match):
        emoji = match.group(0)
        return emoji_map.get(emoji, emoji)
    return EMOJI_REGEX.sub(replace_fn, text)

def get_emojis_in_order(text: str) -> List[str]:
    # Keep duplicates and order of appearance, only unique in mapping
    seen = set()
    ordered = []
    for em in EMOJI_REGEX.findall(text):
        if em not in seen:
            ordered.append(em)
            seen.add(em)
    return ordered

def load_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def save_file(filepath: str, content: str):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def process_json_file(src: str, dst: str, emoji_map: dict):
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    def recursive_replace(obj):
        if isinstance(obj, str):
            return replace_emojis(obj, emoji_map)
        elif isinstance(obj, list):
            return [recursive_replace(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: recursive_replace(v) for k, v in obj.items()}
        return obj
    new_data = recursive_replace(data)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

def process_csv_file(src: str, dst: str, emoji_map: dict):
    with open(src, "r", encoding="utf-8", newline='') as f:
        reader = list(csv.reader(f))
    new_rows = []
    for row in reader:
        new_row = [replace_emojis(cell, emoji_map) for cell in row]
        new_rows.append(new_row)
    with open(dst, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

def process_txt_file(src: str, dst: str, emoji_map: dict):
    text = load_file(src)
    new_text = replace_emojis(text, emoji_map)
    save_file(dst, new_text)

def process_md_file(src: str, dst: str, emoji_map: dict):
    process_txt_file(src, dst, emoji_map)

def process_xml_file(src: str, dst: str, emoji_map: dict):
    tree = ET.parse(src)
    root = tree.getroot()
    def recursive_xml(elem):
        if elem.text:
            elem.text = replace_emojis(elem.text, emoji_map)
        if elem.tail:
            elem.tail = replace_emojis(elem.tail, emoji_map)
        for child in elem:
            recursive_xml(child)
    recursive_xml(root)
    tree.write(dst, encoding="utf-8", xml_declaration=True)

class MyHTMLParser(HTMLParser):
    def __init__(self, emoji_map):
        super().__init__()
        self.emoji_map = emoji_map
        self.result = []
    def handle_starttag(self, tag, attrs):
        attr_str = ''.join([f' {k}="{v}"' for k, v in attrs])
        self.result.append(f"<{tag}{attr_str}>")
    def handle_endtag(self, tag):
        self.result.append(f"</{tag}>")
    def handle_data(self, data):
        self.result.append(replace_emojis(data, self.emoji_map))
    def handle_entityref(self, name):
        self.result.append(f"&{name};")
    def handle_charref(self, name):
        self.result.append(f"&#{name};")
    def get_html(self):
        return "".join(self.result)

def process_html_file(src: str, dst: str, emoji_map: dict):
    text = load_file(src)
    parser = MyHTMLParser(emoji_map)
    parser.feed(text)
    save_file(dst, parser.get_html())

def main():
    src_dir = os.path.join(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    files = [f for f in os.listdir(src_dir)
             if os.path.isfile(os.path.join(src_dir, f))
             and f.lower().endswith(SUPPORTED_EXTS)
             and not f.startswith("output")]
    for filename in files:
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(output_dir, filename)
        print(f"Processing {filename}")
        # Extract all emojis in file, in order
        text = load_file(src_path)
        original_emojis = get_emojis_in_order(text)
        if not original_emojis:
            print(f"  No emojis found in {filename}, skip.")
            continue
        emoji_map = build_emoji_map(original_emojis, ANDROID_EMOJI_POOL)
        ext = os.path.splitext(filename)[-1].lower()
        if ext == ".json":
            process_json_file(src_path, dst_path, emoji_map)
        elif ext == ".txt":
            process_txt_file(src_path, dst_path, emoji_map)
        elif ext == ".md":
            process_md_file(src_path, dst_path, emoji_map)
        elif ext == ".csv":
            process_csv_file(src_path, dst_path, emoji_map)
        elif ext == ".xml":
            process_xml_file(src_path, dst_path, emoji_map)
        elif ext in (".html", ".htm"):
            process_html_file(src_path, dst_path, emoji_map)
        else:
            print(f"  Unsupported file type: {filename}")

if __name__ == "__main__":
    main()
