import os
import sys
import gc

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'

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

    separator = Separator('spleeter:2stems', multiprocess=False)
    output_base_folder = "karaoke_output"
    
    if not os.path.exists(output_base_folder):
        os.makedirs(output_base_folder)

    try:
        separator.separate_to_file(input_file_path, output_base_folder, duration=90)
        print("Success: Separation completed successfully.")
        del separator
        gc.collect()
        return True
    except Exception as e:
        print(f"Error: Separation failed due to: {e}")
        gc.collect()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        separate_vocals(sys.argv[1])
    else:
        print("Error: No input file path provided.")
        sys.exit(1)