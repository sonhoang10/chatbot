# - Tải và cài đặt ffmpeg từ trang chủ FFmpeg. (Download and install ffmpeg from the official FFmpeg website: https://ffmpeg.org/download.html)
# - Thêm đường dẫn tới thư mục bin của ffmpeg vào biến môi trường PATH (Add the path to the ffmpeg bin directory to the PATH environment variable.)
import os
import wave
from pydub import AudioSegment
import uuid

class WavProcessor:
    def __init__(self, output_dir, result_dir, sample_rate=44100, channels=2):
        self.output_dir = output_dir
        self.result_dir = result_dir
        self.sample_rate = sample_rate
        self.channels = channels

        # Tạo các thư mục nếu chưa tồn tại (Create folders if they do not exist)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.result_dir, exist_ok=True)

    # Hàm để đọc các thông số của file WAV (Function to check WAV file parameters)
    def check_wave_params(self, file_path):
        with wave.open(file_path, 'rb') as wav_file:
            params = wav_file.getparams()
        return params

    # Hàm để đọc dữ liệu từ file WAV (Function to read data from a WAV file)
    def read_wave(self, file_path):
        with wave.open(file_path, 'rb') as wav_file:
            params = wav_file.getparams()
            frames = wav_file.readframes(params.nframes)
        return params, frames

    # Hàm để ghi dữ liệu vào một file WAV mới (Function to write data to a new WAV file)
    def write_wave(self, file_path, params, frames):
        with wave.open(file_path, 'wb') as wav_file:
            wav_file.setparams(params)
            wav_file.writeframes(frames)

    # Hàm để gộp nhiều file WAV (Function to merge multiple WAV files)
    def merge_waves(self, file_list, output_file):
        all_frames = []
        params = None
        inconsistent_files = []

        for file in file_list:
            file_params, file_frames = self.read_wave(file)
            
            # Đảm bảo tất cả các file có cùng thông số (không bao gồm nframes) (Ensure all files have the same parameters except for nframes)
            if params is None:
                params = file_params
            elif (file_params.nchannels != params.nchannels or 
                  file_params.sampwidth != params.sampwidth or 
                  file_params.framerate != params.framerate):
                inconsistent_files.append(file)
                continue  # Bỏ qua file có thông số khác (Skip files with different parameters)
            
            all_frames.append(file_frames)

        if inconsistent_files:
            print("Các file WAV sau có thông số khác và đã bị bỏ qua:") # The following WAV files have different parameters and were skipped:
            for file in inconsistent_files:
                print(file)

        if not all_frames:
            raise ValueError("Không có file WAV nào có cùng thông số để gộp.")

        # Gộp dữ liệu từ tất cả các file (Merge data from all files)
        merged_frames = b''.join(all_frames)
        
        # Ghi dữ liệu gộp vào một file WAV mới (Write the merged data to a new WAV file)
        self.write_wave(output_file, params, merged_frames)

    # Hàm để chuyển đổi file WAV về cùng định dạng (Function to convert WAV files to the same format)
    def convert_wav(self, file_path, output_path):
        audio = AudioSegment.from_wav(file_path)
        audio = audio.set_frame_rate(self.sample_rate).set_channels(self.channels)
        audio.export(output_path, format="wav")

    # Hàm để xóa các file converted trong thư mục (Function to delete converted files in a directory)
    def delete_converted_files(self, converted_files):
        for file_path in converted_files:
            if os.path.isfile(file_path):
                os.remove(file_path)
                # print(f"Đã xóa file: {file_path}") # File deleted: {file_path}

    # Hàm xử lý toàn bộ quá trình (Function to process all files)
    def process_files(self, file_names, output_file_name):
        # Đảm bảo danh sách file_names chứa đường dẫn tuyệt đối (Ensure file_names contains absolute paths)
        input_files = file_names
        output_files = [os.path.join(self.output_dir, os.path.basename(file_name)) for file_name in file_names]

        # Chuyển đổi các file WAV (Convert WAV files)
        for input_file, output_file in zip(input_files, output_files):
            self.convert_wav(input_file, output_file)

        print("Chuyển đổi hoàn tất") # Conversion complete

        # Gộp các file WAV đã chuyển đổi (Combine the converted WAV files)
        merged_file_path = os.path.join(self.result_dir, output_file_name)
        self.merge_waves(output_files, merged_file_path)

        print("Gộp file hoàn tất. File đã được lưu tại:", merged_file_path)

        # Xóa các file đã chuyển đổi (Delete the converted files)
        self.delete_converted_files(output_files)

def run_combine_audio(file_names, result_dir, output_file_name):
    output_dir = os.path.join(os.getcwd(), 'Audio_processing')  # Đường dẫn thư mục chứa các file WAV đã chuyển đổi (Directory for converted WAV files)
    os.makedirs(output_dir, exist_ok=True) #Tạo file xử lý nếu chưa tạo (Create a processing file if not already created)

    processor = WavProcessor(output_dir, result_dir)  # Tạo một đối tượng của WavProcessor (Create a WavProcessor instance)

    # Xử lý các file (Process the files)
    processor.process_files(file_names, output_file_name)

# Usage example
if __name__ == "__main__":
    result_dir = 'C:\\Son\\TTS_MAIN\\chatbot\\sessions\\abc123\\AudioFolder' # Đường dẫn thư mục chứa kết quả gộp file (Directory for merged files)
    #For example: ['C:\\Son\\TTS_MAIN\\chatbot\\sessions\\abc123\\AudioFolder\\141ca31c-7496-4aca-8b77-1be5f465511d.wav', 'C:\\Son\\TTS_MAIN\\chatbot\\sessions\\abc123\\AudioFolder\\7e97d671-4312-47cb-a962-7fe137e5518e.wav']
    file_names = ['C:\\Son\\TTS_MAIN\\chatbot\\sessions\\abc123\\AudioFolder\\26dda8fd-ad3f-41ed-aee9-86bd1aae8737.wav','C:\\Son\\TTS_MAIN\\chatbot\\sessions\\abc123\\AudioFolder\\805dcf98-0d2d-42da-bc2f-2e1608f87a89.wav']  # Danh sách các file WAV đầu vào (List of input WAV files) 
    output_file_name = str(uuid.uuid4()) + ".wav" #Đặt tên cho file output (name the output_file)
    run_combine_audio(file_names, result_dir, output_file_name) # Chạy chương trình (Run the program)
