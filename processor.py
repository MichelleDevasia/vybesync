import os
import sys

def separate_vocals(input_file_path):
    # Validate input file existence
    if not input_file_path or not os.path.exists(input_file_path):
        print(f"Error: Input file '{input_file_path}' does not exist.")
        return False
        
    print(f"Initializing AI stem separation for: {input_file_path}")
    
    # Import Spleeter inside the function to avoid slow initializations or startup errors in checks
    try:
        from spleeter.separator import Separator
    except ImportError as ie:
        print(f"Error: Spleeter library is not installed or import failed. Details: {ie}")
        return False

    separator = Separator('spleeter:2stems')
    output_base_folder = "karaoke_output"
    
    if not os.path.exists(output_base_folder):
        os.makedirs(output_base_folder)

    try:
        separator.separate_to_file(input_file_path, output_base_folder)
        print("Success: Separation completed successfully.")
        return True
    except Exception as e:
        print(f"Error: Separation failed due to: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        separate_vocals(sys.argv[1])
    else:
        print("Error: No input file path provided.")
        sys.exit(1)