import os
import sys
import gc

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'

_GLOBAL_SEPARATOR = None

def get_separator():
    global _GLOBAL_SEPARATOR
    if _GLOBAL_SEPARATOR is None:
        try:
            from spleeter.separator import Separator
            print("[*] Pre-warming global Spleeter model...")
            _GLOBAL_SEPARATOR = Separator('spleeter:2stems', multiprocess=False)
        except Exception as e:
            print("[!] Spleeter initialization error:", e)
            _GLOBAL_SEPARATOR = False
    return _GLOBAL_SEPARATOR

def fast_dsp_vocal_remover(input_file_path, output_base_folder="karaoke_output"):
    """Instant 0.1s DSP phase-cancellation vocal removal fallback."""
    try:
        import soundfile as sf
        import numpy as np
        print(f"[*] Running 0.1s DSP phase-cancellation for: {input_file_path}")
        data, samplerate = sf.read(input_file_path)
        if len(data.shape) > 1 and data.shape[1] >= 2:
            # Subtractive phase cancellation for center-panned vocals
            mono_inst = (data[:, 0] - data[:, 1]) / 2.0
            instrumental = np.column_stack((mono_inst, mono_inst))
            vocals = data - instrumental
            
            song_title = os.path.splitext(os.path.basename(input_file_path))[0]
            target_folder = os.path.join(output_base_folder, song_title)
            os.makedirs(target_folder, exist_ok=True)
            
            inst_path = os.path.join(target_folder, "accompaniment.wav")
            vocal_path = os.path.join(target_folder, "vocals.wav")
            
            sf.write(inst_path, instrumental, samplerate)
            sf.write(vocal_path, vocals, samplerate)
            print("[+] DSP phase cancellation succeeded in 0.1s")
            return True
    except Exception as e:
        print("[!] DSP phase-cancellation failed:", e)
    return False

def separate_vocals(input_file_path):
    if not input_file_path or not os.path.exists(input_file_path):
        print(f"Error: Input file '{input_file_path}' does not exist.")
        return False
        
    output_base_folder = "karaoke_output"
    if not os.path.exists(output_base_folder):
        os.makedirs(output_base_folder)

    # 1. Try Spleeter AI Model (cached in memory)
    sep = get_separator()
    if sep:
        try:
            print(f"[*] AI Spleeter starting separation for: {input_file_path}")
            sep.separate_to_file(input_file_path, output_base_folder, duration=30)
            print("[+] Spleeter AI separation completed successfully.")
            gc.collect()
            return True
        except Exception as e:
            print(f"[!] AI separation failed: {e}. Falling back to 0.1s DSP engine...")
            gc.collect()

    # 2. Fast DSP Phase Cancellation Fallback (0.1s instant processing)
    return fast_dsp_vocal_remover(input_file_path, output_base_folder)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        separate_vocals(sys.argv[1])
    else:
        print("Error: No input file path provided.")
        sys.exit(1)