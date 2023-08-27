from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from evtx import PyEvtxParser
import re
from lxml import etree
import socket

app = Flask(__name__)

# Create the 'uploads' folder if it doesn't exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Set local hostnames
# local_hostname = socket.gethostname()
# LOCAL_HOSTNAMES = ['localhost', '127.0.0.1', local_hostname]

# def is_local_host(host):
#     return host in LOCAL_HOSTNAMES

# @app.route('/favicon.ico')
# def favicon():
#     print(">>favicon")
#     return send_from_directory(os.path.join(app.root_path, 'static/img'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    host = request.host.split(':')[0]
    # is_local = is_local_host(host)
    print("[INFO] Deploy " + host)
    uploaded_files = os.listdir('uploads')
    return render_template('upload.html', uploaded_files=uploaded_files)

@app.route('/parse', methods=['POST'])
def parse_evtx():
    evtx_file = request.files['evtx_file']
    if evtx_file:
        file_path = os.path.join('uploads', evtx_file.filename)
        print(file_path)

        if not os.path.isfile(file_path):
            print("[INFO] SAVE-FILE :", file_path)
            evtx_file.save(file_path)

        events_generator = parse_evtx_file(file_path)
        return stream_template('result.html', events=events_generator, filename=evtx_file.filename)

    return "No file uploaded."

@app.route('/send_filename', methods=['POST'])
def parse_evtx_load_save_file():
    selected_filename = request.form.get('filename')
    file_path = os.path.join('uploads', selected_filename)
    print("[INFO] LOAD-FILE :", file_path)

    return stream_template('result.html', events=parse_evtx_file(file_path), filename=selected_filename)

@app.route("/delete_file", methods=["POST"])
def delete_file():
    data = request.get_json()
    filename = data.get("filename")
    evtx_file_path = os.path.join("uploads", filename)
    print("[INFO] DELETE-FILE :", evtx_file_path)

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
    print(">>parse_evtx_file")
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
    event_id_match = re.search(r'<EventID(?:\s+Qualifiers="\d+")?>(\d+)</EventID>', event_data)
    return event_id_match.group(1) if event_id_match else None

def extract_machine_name(event_data):
    machine_name_match = re.search(r'<Computer>(.*?)</Computer>', event_data)
    return machine_name_match.group(1) if machine_name_match else None

def remove_rendering_INFOo(event_data):
    return re.sub(r'<RenderingINFOo[^>]*>.*?</RenderingINFOo>\n', '', event_data, flags=re.DOTALL)

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
