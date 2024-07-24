import re
import os

class Vietnorm:
    def __init__(self):
        self.load_dictionary()
        self.load_mappings()
        self.compile_rules()

    def load_dictionary(self):
        self.directory = os.path.dirname(os.path.abspath(__file__))
        dictDirectory = os.path.join(self.directory, 'Dict', 'Popular.txt')
        dictDirectory = os.path.normpath(dictDirectory)
        self.vietnamese_syllables = self.load_file(dictDirectory)

    def load_mappings(self):
        mapping_files = [
            'Acronyms.txt', 'Acronyms_shorten.txt', 'BaseUnit.txt',
            'CurrencyUnit.txt', 'LetterSoundEN.txt', 'LetterSoundVN.txt',
            'Number.txt', 'PrefixUnit.txt', 'Symbol.txt', 'Teencode.txt'
        ]
        self.mappings = {}
        for file in mapping_files:
            name = file.split('.')[0]
            self.mappings[name] = self.load_mapping(f'{self.directory}/Mapping/{file}')

    def load_file(self, filename):
        with open(filename, 'r', encoding='utf-16 BE') as f:
            return set(f.read().splitlines())

    def load_mapping(self, filename):
        mapping = {}
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    key, value = parts
                    mapping[key] = value
        return mapping

    def compile_rules(self):
        self.rules = []
        rule_files = sorted(os.listdir(f'{self.directory}/RegexRule'))
        for file in rule_files:
            with open(f'{self.directory}/RegexRule/{file}', 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):  # Skip empty lines and comments
                        continue
                    parts = line.split('\t')
                    if len(parts) != 2:
                        #print(f"Warning: Skipping invalid rule in {file} at line {line_number}: {line}")
                        continue
                    pattern, replacement = parts
                    try:
                        self.rules.append((re.compile(pattern), replacement))
                    except re.error as e:
                        print(f"Error compiling regex in {file} at line {line_number}: {e}")

    def apply_rules(self, text):
        for pattern, replacement in self.rules:
            text = pattern.sub(lambda m: eval(f'f"{replacement}"'), text)
        return text

    def dictionary_checking(self, text):
        words = text.split()
        normalized_words = []
        for word in words:
            if word in self.vietnamese_syllables:
                normalized_words.append(word)
            elif word in self.mappings['Acronyms']:
                normalized_words.append(self.mappings['Acronyms'][word])
            elif word in self.mappings['Teencode']:
                normalized_words.append(self.mappings['Teencode'][word])
            else:
                normalized_words.append(self.handle_unknown_word(word))
        return ' '.join(normalized_words)

    def handle_unknown_word(self, word):
        if word.isupper():
            return ' '.join([self.mappings['LetterSoundEN'].get(c, c) for c in word])
        elif any(c.isalpha() for c in word) and not word.isupper():
            return word  # Keep as is for backend processing
        else:
            return ' '.join([self.mappings['LetterSoundVN'].get(c, c) for c in word])

    def normalize(self, text, punc=False, unknown=True, lower=True, rule=False):
        # Apply rules
        text = self.apply_rules(text)

        if not rule:
            # Apply dictionary checking
            text = self.dictionary_checking(text)

        if not punc:
            # Replace non-stop punctuation
            text = re.sub(r'[^\.,\s\w]', '', text)

        if lower:
            text = text.lower()

        if not unknown:
            # Remove words not in the Vietnamese syllable dictionary
            words = text.split()
            text = ' '.join([w for w in words if w in self.vietnamese_syllables])

        # Process the output as described in the paper
        lines = text.split('\n')
        processed_output = ". ".join(line.strip() for line in lines if line.strip())

        return processed_output
    
    def standardize_output(self, text):
        # Remove no voice marks
        text = re.sub(r'[\(\)\[\]]', '', text)
        
        # Replace all punctuation marks with comma and dot
        text = re.sub(r'[;:!?]', '.', text)
        
        # Remove duplicate spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove spaces before punctuation and ensure space after
        text = re.sub(r'\s+([.,])', r'\1', text)
        text = re.sub(r'([.,])(?!\s)', r'\1 ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text

def TTSnorm(text, punc=False, unknown=True, lower=True, rule=False):
    normalizer = Vietnorm()
    normalized_text = normalizer.normalize(text, punc=punc, unknown=unknown, lower=lower, rule=rule)
    return normalized_text

# Example usage
# if __name__ == "__main__":
#     input_text = "Đây là 1 ví dụ về chuẩn hóa văn bản tiếng Việt!"
#     normalized_text = TTSnorm(input_text, punc=True, unknown=True, lower=True, rule=False)
#     print(normalized_text)