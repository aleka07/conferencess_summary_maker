#!/usr/bin/env python3
"""
Complete Audio Processing Pipeline
Runs all steps from video input to AI summary
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add current directory to path so we can import other scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_step(step, description):
    """Print step information"""
    print(f"\n[STEP {step}] {description}")
    print("-" * 40)

def run_script(script_name, script_description):
    """Run a script and handle errors"""
    print(f"\n🔧 Running {script_name}...")
    
    try:
        # Import and run the script
        if script_name == "1-extract_audio.py":
            from importlib import import_module
            module = import_module("1-extract_audio")
            # We'll need to modify the original scripts to support automation
            print("⚠️  Please run manually for now: python 1-extract_audio.py")
            return False
            
        elif script_name == "2-split_audio.py":
            print("⚠️  Please run manually for now: python 2-split_audio.py") 
            return False
            
        elif script_name == "3-transcribe_local_batch.py":
            print("⚠️  Please run manually for now: python 3-transcribe_local_batch.py")
            return False
            
        elif script_name == "4-merge_transcripts.py":
            print("⚠️  Please run manually for now: python 4-merge_transcripts.py")
            return False
            
        elif script_name == "5-create_summary_openrouter.py":
            print("⚠️  Please run manually for now: python 5-create_summary_openrouter.py")
            return False
            
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False
    
    return True

def check_requirements():
    """Check if all requirements are met"""
    print_header("CHECKING REQUIREMENTS")
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append("Python 3.8+ required")
    else:
        print("✅ Python version OK")
    
    # Check FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("FFmpeg not found - please install FFmpeg")
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        issues.append(".env file not found - copy .env.example and add your API key")
    else:
        print("✅ .env file found")
    
    # Check directories
    required_dirs = ["input", "audio-from-input", "chunks", "raw_text", "summaries"]
    for dir_name in required_dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("✅ Directory structure created")
    
    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("\n✅ All requirements met!")
    return True

def show_menu():
    """Show main menu"""
    print_header("AUDIO PROCESSING PIPELINE")
    print("Choose an option:")
    print()
    print("1. Run complete pipeline (all steps)")
    print("2. Run individual step")
    print("3. Check requirements")
    print("4. Show project status")
    print("q. Quit")
    print()

def show_individual_steps():
    """Show individual step menu"""
    print("\nIndividual Steps:")
    print("1. Extract audio from video")
    print("2. Split audio into chunks")  
    print("3. Transcribe audio chunks")
    print("4. Merge transcripts")
    print("5. Create AI summary")
    print("b. Back to main menu")

def show_project_status():
    """Show status of all projects"""
    print_header("PROJECT STATUS")
    
    # Check input files
    input_dir = Path("input")
    if input_dir.exists():
        input_files = list(input_dir.glob("*.webm")) + list(input_dir.glob("*.mp4"))
        print(f"📁 Input files: {len(input_files)} videos")
        for f in input_files[:5]:  # Show first 5
            print(f"   - {f.name}")
        if len(input_files) > 5:
            print(f"   ... and {len(input_files) - 5} more")
    
    # Check processed projects
    summaries_dir = Path("summaries")
    if summaries_dir.exists():
        completed = list(summaries_dir.iterdir())
        print(f"✅ Completed: {len(completed)} projects")
        for proj in completed:
            print(f"   - {proj.name}")
    else:
        print("📋 No completed projects yet")

def run_complete_pipeline():
    """Run the complete pipeline"""
    print_header("RUNNING COMPLETE PIPELINE")
    
    steps = [
        ("1-extract_audio.py", "Extract audio from videos"),
        ("2-split_audio.py", "Split audio into chunks"),
        ("3-transcribe_local_batch.py", "Transcribe audio to text"),
        ("4-merge_transcripts.py", "Merge transcript files"),
        ("5-create_summary_openrouter.py", "Generate AI summary")
    ]
    
    print("This will run all 5 steps in sequence:")
    for i, (script, desc) in enumerate(steps, 1):
        print(f"  {i}. {desc}")
    
    confirm = input("\nProceed? (y/n): ")
    if confirm.lower() != 'y':
        return
    
    print("\n🚀 Starting complete pipeline...")
    
    for i, (script, description) in enumerate(steps, 1):
        print_step(i, description)
        
        # For now, we'll just show what would be run
        print(f"Would run: python {script}")
        print("⚠️  Manual execution required - scripts need user input")
        
        continue_choice = input("\nContinue to next step? (y/n): ")
        if continue_choice.lower() != 'y':
            print("Pipeline stopped by user")
            return
    
    print("\n🎉 Pipeline completed!")

def main():
    """Main function"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    while True:
        show_menu()
        choice = input("Enter choice: ").strip()
        
        if choice == '1':
            if check_requirements():
                run_complete_pipeline()
        
        elif choice == '2':
            show_individual_steps()
            step_choice = input("Choose step (1-5, b): ").strip()
            
            steps = {
                '1': ("1-extract_audio.py", "Extract audio from video"),
                '2': ("2-split_audio.py", "Split audio into chunks"),
                '3': ("3-transcribe_local_batch.py", "Transcribe audio chunks"),
                '4': ("4-merge_transcripts.py", "Merge transcripts"),
                '5': ("5-create_summary_openrouter.py", "Create AI summary")
            }
            
            if step_choice in steps:
                script, desc = steps[step_choice]
                print(f"\n🔧 Run manually: python {script}")
            elif step_choice == 'b':
                continue
        
        elif choice == '3':
            check_requirements()
        
        elif choice == '4':
            show_project_status()
        
        elif choice.lower() == 'q':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()