#!/usr/bin/env python3
"""
Enhanced Merge Transcripts - with progress bars and better UX
Improved version of 4-merge_transcripts.py
"""

import os
import sys
from pathlib import Path

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("💡 Install tqdm for progress bars: pip install tqdm")

# Configuration
RAW_TEXT_BASE_DIR = "raw_text"
MERGED_FILENAME = "_full_transcript.txt"
CHUNK_DURATION_MINUTES = 10

class ProgressBar:
    """Simple progress bar fallback if tqdm not available"""
    def __init__(self, total, desc="Processing"):
        self.total = total
        self.current = 0
        self.desc = desc
        
    def update(self, n=1):
        self.current += n
        percent = (self.current / self.total) * 100
        bar_length = 30
        filled = int(bar_length * self.current // self.total)
        bar = '█' * filled + '-' * (bar_length - filled)
        sys.stdout.write(f'\r{self.desc}: |{bar}| {percent:.1f}%')
        sys.stdout.flush()
        
    def close(self):
        print()  # New line after progress bar

def get_progress_bar(total, desc):
    """Get appropriate progress bar"""
    if HAS_TQDM:
        return tqdm(total=total, desc=desc, unit="файл")
    else:
        return ProgressBar(total, desc)

def get_meeting_folders(directory):
    """Find meeting folders in transcription directory"""
    folders = []
    base_path = Path(directory)
    
    if not base_path.exists():
        print(f"❌ Папка '{directory}' не найдена.")
        return folders
        
    for item in base_path.iterdir():
        if item.is_dir():
            folders.append(item.name)
            
    return sorted(folders)

def analyze_meeting_folder(meeting_path):
    """Analyze meeting folder and return statistics"""
    txt_files = [f for f in meeting_path.glob("*.txt") if f.name != MERGED_FILENAME]
    merged_file = meeting_path / MERGED_FILENAME
    
    return {
        'txt_count': len(txt_files),
        'has_merged': merged_file.exists(),
        'merged_size': merged_file.stat().st_size if merged_file.exists() else 0,
        'txt_files': sorted(txt_files, key=lambda x: x.name)
    }

def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def merge_transcripts(meeting_name, force_overwrite=False):
    """Merge transcript files with progress tracking"""
    meeting_path = Path(RAW_TEXT_BASE_DIR) / meeting_name
    output_file = meeting_path / MERGED_FILENAME
    
    print(f"\n📂 Обработка: {meeting_name}")
    
    # Analyze folder
    stats = analyze_meeting_folder(meeting_path)
    
    if stats['txt_count'] == 0:
        print("⚠️  Нет txt файлов для объединения")
        return False
        
    if stats['has_merged'] and not force_overwrite:
        print(f"✅ Файл уже существует ({stats['merged_size']} байт)")
        return True
    
    txt_files = stats['txt_files']
    print(f"📋 Найдено {len(txt_files)} файлов")
    
    # Progress tracking
    progress = get_progress_bar(len(txt_files), "Объединение")
    
    try:
        with output_file.open('w', encoding='utf-8') as outfile:
            for i, txt_file in enumerate(txt_files):
                try:
                    # Read file content
                    content = txt_file.read_text(encoding='utf-8').strip()
                    outfile.write(content)
                    
                    # Add metadata
                    part_num = i + 1
                    start_seconds = i * CHUNK_DURATION_MINUTES * 60
                    end_seconds = part_num * CHUNK_DURATION_MINUTES * 60
                    
                    start_time = format_time(start_seconds)
                    end_time = format_time(end_seconds)
                    
                    metadata = f"\n\n--- Конец Части-{part_num}, Время: {start_time} - {end_time} ---"
                    outfile.write(metadata)
                    
                    if i < len(txt_files) - 1:
                        outfile.write("\n\n")
                        
                except Exception as e:
                    print(f"\n⚠️  Ошибка при чтении {txt_file.name}: {e}")
                    
                # Update progress
                progress.update(1)
                
        progress.close()
        
        # Show results
        final_size = output_file.stat().st_size
        print(f"✅ Успешно! Создан файл: {output_file.name} ({final_size} байт)")
        return True
        
    except Exception as e:
        progress.close()
        print(f"❌ Ошибка: {e}")
        return False

def show_status():
    """Show status of all projects"""
    print("\n" + "="*60)
    print("  СТАТУС ВСЕХ ПРОЕКТОВ")  
    print("="*60)
    
    folders = get_meeting_folders(RAW_TEXT_BASE_DIR)
    
    if not folders:
        print("📭 Нет проектов для обработки")
        return
    
    print(f"Найдено проектов: {len(folders)}\n")
    
    for folder in folders:
        meeting_path = Path(RAW_TEXT_BASE_DIR) / folder
        stats = analyze_meeting_folder(meeting_path)
        
        status = "✅" if stats['has_merged'] else "⏳"
        size_info = f"({stats['merged_size']} байт)" if stats['has_merged'] else ""
        
        print(f"{status} {folder}: {stats['txt_count']} файлов {size_info}")

def main():
    """Main function with improved UX"""
    print("🔄 Объединение транскриптов")
    
    while True:
        folders = get_meeting_folders(RAW_TEXT_BASE_DIR)
        
        if not folders:
            print("📭 В папке 'raw_text' нет папок с транскрипциями")
            break
            
        print(f"\nДоступно проектов: {len(folders)}")
        print("Команды: [номер] - обработать, 'a' - все, 's' - статус, 'q' - выход")
        
        # Show projects with status
        for i, folder in enumerate(folders, 1):
            meeting_path = Path(RAW_TEXT_BASE_DIR) / folder
            stats = analyze_meeting_folder(meeting_path)
            status = "✅" if stats['has_merged'] else "⏳"
            print(f"{i:2}. {status} {folder} ({stats['txt_count']} файлов)")
        
        choice = input("\nВыбор: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 's':
            show_status()
            input("\nНажмите Enter...")
            continue
        elif choice == 'a':
            # Process all
            print("\n🚀 Обработка всех проектов...")
            for folder in folders:
                merge_transcripts(folder, force_overwrite=False)
            input("\n✅ Готово! Нажмите Enter...")
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(folders):
                    selected = folders[index]
                    
                    # Check if already exists
                    meeting_path = Path(RAW_TEXT_BASE_DIR) / selected
                    if (meeting_path / MERGED_FILENAME).exists():
                        overwrite = input("Файл существует. Перезаписать? (y/n): ")
                        force = overwrite.lower() == 'y'
                    else:
                        force = False
                    
                    merge_transcripts(selected, force_overwrite=force)
                    input("\nНажмите Enter...")
                else:
                    print("❌ Неверный номер")
            except ValueError:
                print("❌ Неверный ввод")

if __name__ == "__main__":
    main()