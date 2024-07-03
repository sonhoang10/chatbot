from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        data = request.get_json()
        question = data.get('question')
        # Process the question and generate a response
        response = {'response': f'You asked: {question}'} #return the same question for demonstration
        return jsonify(response)
    return render_template('chatbot.html')

if __name__ == '__main__':
    app.run(debug=True)