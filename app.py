from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from evtx import PyEvtxParser
import re

event_id_pattern = re.compile(r'<EventID(?:\s+Qualifiers="\d+")?>(\d+)</EventID>')
machine_name_pattern = re.compile(r'<Computer>(.*?)</Computer>')

app = Flask(__name__)

# Create the 'uploads' folder if it doesn't exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

@app.route('/')
def index():
    uploaded_files = os.listdir('uploads')
    return render_template('upload.html', uploaded_files=uploaded_files)

@app.route('/parse', methods=['POST'])
def parse_evtx():
    evtx_file = request.files['evtx_file']
    if evtx_file:
        file_path = os.path.join('uploads', evtx_file.filename)

        if not os.path.isfile(file_path):
            evtx_file.save(file_path)

        events_generator = parse_evtx_file(file_path)
        return stream_template('result.html', events=events_generator, filename=evtx_file.filename)

    return "No file uploaded."

@app.route('/send_filename', methods=['POST'])
def parse_evtx_load_save_file():
    selected_filename = request.form.get('filename')
    file_path = os.path.join('uploads', selected_filename)
    return stream_template('result.html', events=parse_evtx_file(file_path), filename=selected_filename)

@app.route("/delete_file", methods=["POST"])
def delete_file():
    data = request.get_json()
    filename = data.get("filename")
    evtx_file_path = os.path.join("uploads", filename)

    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension == ".evtx":
        try:
            os.remove(evtx_file_path)
            return jsonify({"success": True})
        except Exception as e:
            print("Error deleting file:", e)
            return jsonify({"success": False}), 500
    else:
        print("Exception handling: delete file extension is not evtx")
        return jsonify({"success": False}), 500

def stream_template(template_name, **context):
    app.update_template_context(context)
    template = app.jinja_env.get_template(template_name)
    rv = template.stream(context)
    rv.enable_buffering(5)
    return rv   

def parse_evtx_file(file_path):
    parser = PyEvtxParser(file_path)
    
    for record in parser.records():
        event_data = record['data']
        event_data = event_data.replace('<?xml version="1.0" encoding="utf-8"?>\n', "")
        event_data = event_data.replace(" xmlns=\"http://schemas.microsoft.com/win/2004/08/events/event\"", "")
        event_data = remove_rendering_INFOo(event_data)

        event_id = extract_event_id(event_data)
        machine_name = extract_machine_name(event_data)

        event = {
            'event_id': event_id,
            'timestamp': record["timestamp"],
            'machineName': machine_name,
            'data': event_data
        }
        yield event

def extract_event_id(event_data):
    event_id_match = event_id_pattern.search(event_data)
    return event_id_match.group(1) if event_id_match else None

def extract_machine_name(event_data):
    machine_name_match = machine_name_pattern.search(event_data)
    return machine_name_match.group(1) if machine_name_match else None

def remove_rendering_INFOo(event_data):
    return re.sub(r'<RenderingINFOo[^>]*>.*?</RenderingINFOo>\n', '', event_data, flags=re.DOTALL)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
