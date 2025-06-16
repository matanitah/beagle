import os
import shutil

def clean_states():
    """Delete all files from the states folder."""
    states_dir = "states"
    
    # Check if states directory exists
    if os.path.exists(states_dir):
        # Remove all files in the directory
        for filename in os.listdir(states_dir):
            file_path = os.path.join(states_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        print(f"Cleaned {states_dir} directory")
    else:
        print(f"{states_dir} directory does not exist")

if __name__ == "__main__":
    clean_states()
