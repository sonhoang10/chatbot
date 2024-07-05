import pyttsx3
engine = pyttsx3.init() # object creation


engine.save_to_file('Hello World', 'test.mp3')
engine.runAndWait()