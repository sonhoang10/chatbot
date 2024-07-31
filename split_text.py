import re

def split_text_into_sentences(text, max_length):
        sentences = re.split(r'(?<=[.!?]) +', text)  # Split text into sentences
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " "
                current_chunk += sentence
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

# Sử dụng hàm để tách câu từ đoạn văn bản
if __name__ == "__main__":
    prompt = "Cuộc sống hiện đại đang ngày càng trở nên phức tạp và nhanh chóng. Công nghệ thông tin và truyền thông phát triển mạnh mẽ đã tạo ra những cơ hội mới nhưng cũng đồng thời mang lại nhiều thách thức. Internet giúp chúng ta kết nối với nhau dễ dàng hơn, tiếp cận thông tin nhanh chóng và trao đổi ý tưởng, nhưng cũng làm gia tăng áp lực và sự căng thẳng trong cuộc sống hàng ngày. Để đối phó với những thay đổi này, việc duy trì sức khỏe tinh thần và thể chất là rất quan trọng. Chúng ta cần học cách cân bằng giữa công việc và cuộc sống cá nhân, đồng thời phát triển những thói quen lành mạnh để giữ cho bản thân luôn trong trạng thái tốt nhất."
    sentences = split_text_into_sentences(prompt,max_length=250)
    print(sentences)
